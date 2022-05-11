# -*- coding: utf-8 -*-
# pylint: disable=no-self-use
"""
Local Git Store

"""
from flask import current_app, request, session, render_template  # NOQA
from flask_login import current_user  # NOQA
import requests.exceptions

import git
from git import Git as BaseGit, Repo as BaseRepo

from app.modules.assets.models import Asset
from app.modules.users.models import User
import app.extensions.logging as AuditLog  # NOQA
from app.extensions import db, HoustonModel, parallel
from app.utils import HoustonException
from app.version import version

import utool as ut
import logging
import keyword
import pathlib
import shutil
import tqdm
import uuid
import enum
import json
import os


KEYWORD_SET = set(keyword.kwlist)

log = logging.getLogger(__name__)


def compute_xxhash64_digest_filepath(filepath):
    try:
        import xxhash
        import os

        assert os.path.exists(filepath)

        with open(filepath, 'rb') as file_:
            digest = xxhash.xxh64_hexdigest(file_.read())
    except Exception:  # pragma: no cover
        digest = None
    return digest


class _Git(BaseGit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Assign the SSH command to include the id key file for authentication
        self.update_environment(GIT_SSH_COMMAND=current_app.config['GIT_SSH_COMMAND'])


class Repo(BaseRepo):
    GitCommandWrapperType = _Git

    # This class is copied from the original with one minor adjustment
    # to use the class' `GitCommandWrapperType` definition as opposed
    # to the direct reference to the `Git` class.
    # Fixed in https://github.com/gitpython-developers/GitPython/pull/1322
    @classmethod
    def clone_from(
        cls, url, to_path, progress=None, env=None, multi_options=None, **kwargs
    ):
        # git = Git(os.getcwd())
        git = cls.GitCommandWrapperType(os.getcwd())
        if env is not None:
            git.update_environment(**env)
        from git.db import GitCmdObjectDB

        return cls._clone(
            git, url, to_path, GitCmdObjectDB, progress, multi_options, **kwargs
        )


class GitStoreMajorType(str, enum.Enum):
    filesystem = 'filesystem'
    archive = 'archive'
    service = 'service'
    test = 'test'

    unknown = 'unknown'
    error = 'error'
    reject = 'reject'


class GitStore(db.Model, HoustonModel):
    """
    GitStore database model.
    """

    GIT_STORE_NAME = 'git_store'

    GIT_STORE_DATABASE_PATH_CONFIG_NAME = 'GIT_STORE_DATABASE_PATH'

    guid = db.Column(
        db.GUID, default=uuid.uuid4, primary_key=True
    )  # pylint: disable=invalid-name

    git_store_type = db.Column(db.String(length=32))

    major_type = db.Column(
        db.Enum(GitStoreMajorType),
        default=GitStoreMajorType.unknown,
        index=True,
        nullable=False,
    )

    owner_guid = db.Column(
        db.GUID, db.ForeignKey('user.guid'), index=True, nullable=False
    )

    submitter_guid = db.Column(
        db.GUID, db.ForeignKey('user.guid'), index=True, nullable=True
    )

    owner = db.relationship(
        'User',
        backref=db.backref(
            'git_stores',
            primaryjoin='User.guid == GitStore.owner_guid',
            order_by='GitStore.guid',
        ),
        foreign_keys='GitStore.owner_guid',
    )

    submitter = db.relationship(
        'User',
        backref=db.backref(
            'submitted_git_stores',
            primaryjoin='User.guid == GitStore.submitter_guid',
            order_by='GitStore.guid',
        ),
        foreign_keys='GitStore.submitter_guid',
    )

    commit = db.Column(db.String(length=40), nullable=True, unique=True)
    commit_mime_whitelist_guid = db.Column(db.GUID, index=True, nullable=True)
    commit_houston_api_version = db.Column(db.String, index=True, nullable=True)

    description = db.Column(db.String(length=255), nullable=True)

    config = db.Column(db.JSON, default=lambda: {}, nullable=False)

    progress_preparation_guid = db.Column(
        db.GUID, db.ForeignKey('progress.guid'), index=False, nullable=True
    )

    progress_preparation = db.relationship(
        'Progress',
        foreign_keys='GitStore.progress_preparation_guid',
    )

    __mapper_args__ = {
        'confirm_deleted_rows': False,
        'polymorphic_identity': 'gitstore',
        'polymorphic_on': git_store_type,
    }

    def __repr__(self):
        return (
            '<{class_name}('
            'guid={self.guid}, '
            ')>'.format(class_name=self.__class__.__name__, self=self)
        )

    @classmethod
    def filter_for(cls, obj, git_stores):
        assert issubclass(
            obj, cls
        ), 'Cannot filter by a class that does not inherit from GitStore'

        retval = []
        for git_store in git_stores:
            if isinstance(git_store, obj):
                retval.append(git_store)

        return retval

    @classmethod
    def ensure_remote_delay(cls, obj):
        raise NotImplementedError()

    @classmethod
    def get_elasticsearch_schema(cls):
        from app.extensions.git_store.schemas import DetailedGitStoreSchema

        return DetailedGitStoreSchema

    def git_push_delay(self):
        raise NotImplementedError()

    def delete_remote_delay(self):
        raise NotImplementedError()

    def git_commit_metadata_hook(self, local_store_metadata):  # pragma: no cover
        pass

    @property
    def anonymous(self):
        return self.owner is User.get_public_user()

    @property
    def mime_type_whitelist(self):
        if getattr(self, '_mime_type_whitelist', None) is None:
            asset_mime_type_whitelist = current_app.config.get(
                'ASSET_MIME_TYPE_WHITELIST_EXTENSION', {}
            ).keys()
            asset_mime_type_whitelist = sorted(list(map(str, asset_mime_type_whitelist)))

            self._mime_type_whitelist = set(asset_mime_type_whitelist)
        return self._mime_type_whitelist

    @property
    def mime_type_whitelist_guid(self):
        if getattr(self, '_mime_type_whitelist_guid', None) is None:
            self._mime_type_whitelist_guid = ut.hashable_to_uuid(
                sorted(list(self.mime_type_whitelist))
            )
            # Write mime.whitelist.<mime-type-whitelist-guid>.json
            mime_type_whitelist_mapping_filepath = os.path.join(
                current_app.config.get('PROJECT_DATABASE_PATH'),
                'mime.whitelist.%s.json' % (self._mime_type_whitelist_guid,),
            )
            if not os.path.exists(mime_type_whitelist_mapping_filepath):
                log.debug(
                    'Creating new MIME whitelist manifest: %r'
                    % (mime_type_whitelist_mapping_filepath,)
                )
                with open(mime_type_whitelist_mapping_filepath, 'w') as mime_type_file:
                    mime_type_whitelist_dict = {
                        str(self._mime_type_whitelist_guid): sorted(
                            list(self.mime_type_whitelist)
                        ),
                    }
                    mime_type_file.write(json.dumps(mime_type_whitelist_dict))
        return self._mime_type_whitelist_guid

    def user_is_owner(self, user):
        return user is not None and user == self.owner

    def get_config_field(self, field):
        return self.config.get(field) if isinstance(self.config, dict) else None

    def _ensure_repository_files(self):
        local_store_path = self.get_absolute_path()

        # Git Store Repo Structure:
        #     _db/<self.GIT_STORE_NAME>/<GUID>/
        #         - .git/
        #         - _<self.GIT_STORE_NAME>/
        #         - - <user's uploaded data>
        #         - _assets/
        #         - - <symlinks into _<self.GIT_STORE_NAME>/ folder> with name <asset GUID >.ext --> ../_<self.GIT_STORE_NAME>/path/to/asset/original_name.ext
        #         - metadata.json

        if not os.path.exists(local_store_path):
            # Initialize local repo
            log.info(
                'Creating %s structure: %r'
                % (
                    self.GIT_STORE_NAME,
                    local_store_path,
                )
            )
            os.mkdir(local_store_path)

        # Create the repo
        git_path = os.path.join(local_store_path, '.git')
        if not os.path.exists(git_path):
            repo = Repo.init(local_store_path)
            assert len(repo.remotes) == 0
            git_remote_public_name = current_app.config.get('GIT_PUBLIC_NAME', None)
            git_remote_email = current_app.config.get('GIT_EMAIL', None)
            assert None not in [git_remote_public_name, git_remote_email]
            repo.git.config('user.name', git_remote_public_name)
            repo.git.config('user.email', git_remote_email)
        else:
            repo = Repo(local_store_path)

        local_uploads_path = os.path.join(local_store_path, '_uploads')
        if not os.path.exists(local_uploads_path):
            os.mkdir(local_uploads_path)
        pathlib.Path(os.path.join(local_uploads_path, '.touch')).touch()

        assets_path = os.path.join(local_store_path, '_assets')
        if not os.path.exists(assets_path):
            os.mkdir(assets_path)
        pathlib.Path(os.path.join(assets_path, '.touch')).touch()

        # We moved the derived path, so clean-up the old location
        old_derived_path = os.path.join(assets_path, 'derived')
        if os.path.exists(old_derived_path):
            shutil.rmtree(old_derived_path)

        local_derived_path = os.path.join(local_store_path, '_derived')
        if not os.path.exists(local_derived_path):
            os.mkdir(local_derived_path)
        pathlib.Path(os.path.join(local_derived_path, '.touch')).touch()

        metadata_path = os.path.join(local_store_path, '_metadata')
        if not os.path.exists(metadata_path):
            os.mkdir(metadata_path)
        pathlib.Path(os.path.join(metadata_path, '.touch')).touch()

        metadata_path = os.path.join(local_store_path, 'metadata.json')
        if not os.path.exists(metadata_path):
            with open(metadata_path, 'w') as metatdata_file:
                json.dump({}, metatdata_file)

        return repo

    def git_write_upload_file(self, upload_file):
        repo = self.ensure_repository()
        file_repo_path = os.path.join(
            repo.working_tree_dir, '_uploads', upload_file.filename
        )
        upload_file.save(file_repo_path)
        log.info('Wrote file upload and added to local repo: %r' % (file_repo_path,))

    def git_copy_path(self, path):
        absolute_path = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(path):
            raise IOError('The path %r does not exist.' % (absolute_path,))

        repo = self.ensure_repository()
        repo_path = os.path.join(repo.working_tree_dir, '_uploads')

        absolute_path = absolute_path.rstrip('/')
        repo_path = repo_path.rstrip('/')
        absolute_path = '%s/' % (absolute_path,)
        repo_path = '%s/' % (repo_path,)

        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)

        shutil.copytree(absolute_path, repo_path)

    def git_copy_file_add(self, filepath):
        from app.utils import get_stored_filename

        absolute_filepath = os.path.abspath(os.path.expanduser(filepath))
        if not os.path.exists(absolute_filepath):
            raise IOError('The filepath %r does not exist.' % (absolute_filepath,))

        repo = self.ensure_repository()
        repo_path = os.path.join(repo.working_tree_dir, '_uploads')
        _, filename = os.path.split(absolute_filepath)
        stored_filename = get_stored_filename(filename)
        repo_filepath = os.path.join(repo_path, stored_filename)

        shutil.copyfile(absolute_filepath, repo_filepath)

        return repo_filepath

    def git_commit(
        self,
        message,
        realize=True,
        update=True,
        commit=None,
        input_filenames=[],
        **kwargs,
    ):
        if self.progress_preparation:
            self.progress_preparation = self.progress_preparation.config()

        # Step 1
        #   Description: Setup of the repository and init one JSON file
        #   Delay: nearly instant, < 1.0 seconds
        #   Percentage: 1% (0% -> 1%)
        repo = self.ensure_repository()

        self.init_metadata()

        if self.progress_preparation:
            self.progress_preparation.set(1)

        # Step 2
        #   Description: Unpack zip files and archives submitted to the repo, currently not implemented
        #   Delay: no-op, << 1.0 seconds
        #   Percentage: 0% (1% -> 1%)
        if realize:
            self.realize_local_store()

        if self.progress_preparation:
            self.progress_preparation.set(1)

        # Step 3
        #   Description: Walk the files in the repo and convert appropriate files to Assets and establish symlinks
        #   Delay: the majority of the processing, unbounded seconds
        #   Percentage: 89% (1% -> 90%)
        if update:
            self.update_asset_symlinks(input_filenames=input_filenames, **kwargs)

        if self.progress_preparation:
            self.progress_preparation.set(90)

        # Step 4
        #   Description: Commit the files into the repo into the git repository, requires hashing all of the files
        #   Delay: a meaningful overhead, but should still be relatively quick, unbounded seconds (Step 4 << Step 3)
        #   Percentage: 9% (90% -> 99%)
        if commit in [True] or (
            commit not in [False] and current_app.config['UPLOADS_GIT_COMMIT']
        ):
            # repo.index.add('.gitignore')
            repo.index.add('_uploads/')
            repo.index.add('_assets/')
            repo.index.add('_metadata/')
            repo.index.add('metadata.json')

            new_commit = repo.index.commit(message)

            self.update_metadata_from_commit(new_commit)

        if self.progress_preparation:
            self.progress_preparation.set(99)

        # Step 5
        #   Description: Update the Git Store's metadata using the git commit hash and other metadata
        #   Delay: nearly instant, < 1.0 seconds
        #   Percentage: 1% (99% -> 100%)
        if update:
            self.update_metadata_from_hook()

        # Update the git store's preparation status
        self.post_preparation_hook()

        if self.progress_preparation:
            self.progress_preparation.set(100)

    def post_preparation_hook(self):
        # Currently no hook
        raise NotImplementedError()

    def git_commit_delay(self, input_filenames):
        from app.extensions.git_store.tasks import git_commit

        # Start the git_commit that will process the assets (update=True) and commit the new files to the Git repo (commit=True)
        description = 'Tus collect commit for GitStore %r' % (self.guid,)
        if current_app.testing:
            # When testing, run on-demand and don't use celery workers
            git_commit(str(self.guid), description, input_filenames)
            promise = None
        else:
            promise = git_commit.delay(str(self.guid), description, input_filenames)

        if self.progress_preparation and promise:
            with db.session.begin():
                self.progress_preparation.celery_guid = promise.id
                db.session.merge(self.progress_preparation)

    def init_metadata(self):
        local_store_path = self.get_absolute_path()
        local_store_metadata_path = os.path.join(local_store_path, 'metadata.json')

        assert os.path.exists(local_store_metadata_path)
        with open(local_store_metadata_path, 'r') as local_store_metadata_file:
            local_store_metadata = json.load(local_store_metadata_file)

        local_store_metadata['commit_mime_whitelist_guid'] = str(
            self.mime_type_whitelist_guid
        )
        local_store_metadata['commit_houston_api_version'] = str(version)

        with open(local_store_metadata_path, 'w') as local_store_metadata_file:
            json.dump(local_store_metadata, local_store_metadata_file)

    def git_pull(self):
        repo = self.get_repository()
        assert repo is not None

        log.info('Pulling from remote repository')
        try:
            repo.git.pull(repo.remotes.origin, repo.head.ref)
        except git.exc.GitCommandError as e:
            log.info(f'git pull failed for {self.guid}: {str(e)}')
        else:
            log.info('...pulled')

        self.update_metadata_from_repo(repo)

        return repo

    def git_clone(self, project, **kwargs):
        repo = self.get_repository()
        assert repo is None

        local_store_path = self.get_absolute_path()
        remote_url = project.ssh_url_to_repo

        args = (
            remote_url,
            local_store_path,
        )
        log.info('Cloning remote git store:\n\tremote: %r\n\tlocal:  %r' % args)
        repo = Repo.clone_from(remote_url, local_store_path)
        log.info('...cloned')

        repo = self.get_repository()
        assert repo is not None

        self.update_metadata_from_project(project)
        self.update_metadata_from_repo(repo)

        # Traverse the repo and create Asset objects in database
        self.update_asset_symlinks(**kwargs)

        return repo

    @classmethod
    def ensure_store(cls, store_guid, owner=None, **kwargs):
        git_store = cls.query.get(store_guid)
        if git_store is None:
            from app.extensions import db

            if not cls.is_on_remote(store_guid):
                return None

            if owner is None:
                owner = current_user

            git_store = cls(guid=store_guid, owner_guid=owner.guid, **kwargs)

            with db.session.begin():
                db.session.add(git_store)
            db.session.refresh(git_store)

        # Make sure that the repo for this git store exists
        git_store.ensure_repository()

        # Create gitlab project in the background (we won't wait for its
        # completion here)
        cls.ensure_remote_delay(git_store)

        return git_store

    def init_progress_preparation(self, overwrite=False):
        from app.modules.progress.models import Progress

        if self.progress_preparation is not None:
            if not overwrite:
                log.warning(
                    'Git Store %r already has a progress preparation %r'
                    % (
                        self,
                        self.progress_preparation,
                    )
                )
                return

        progress = Progress(description='Git commit for GitStore %r' % (self.guid,))
        with db.session.begin():
            db.session.add(progress)

        with db.session.begin():
            self.progress_preparation_guid = progress.guid
            db.session.merge(self)

        db.session.refresh(self)

    @classmethod
    def create_from_metadata(cls, metadata, foreground=False, **kwargs):
        if metadata.owner is not None and not metadata.owner.is_anonymous:
            git_store_owner = metadata.owner
        else:
            git_store_owner = User.get_public_user()

        if metadata.tus_transaction_id and not metadata.files:
            raise HoustonException(
                log,
                'Tus transaction must contain files',
            )
        if not metadata.files and not git_store_owner.is_researcher:
            raise HoustonException(
                log,
                'Only a Researcher can create a Git Store without any Assets',
            )
        git_store = cls(
            major_type=GitStoreMajorType.filesystem,
            description=metadata.description,
            owner_guid=git_store_owner.guid,
            **kwargs,
        )

        if metadata.anonymous_submitter:
            git_store.submitter = metadata.anonymous_submitter

        with db.session.begin(subtransactions=True):
            db.session.add(git_store)

        log.debug('created %r' % git_store)

        if metadata.tus_transaction_id:
            try:
                added, original_filenames = git_store.import_tus_files(
                    transaction_id=metadata.tus_transaction_id, foreground=foreground
                )
            except Exception:  # pragma: no cover
                log.exception(
                    'create_from_metadata() had problems with import_tus_files(); deleting from db and fs %r'
                    % git_store
                )
                git_store.delete()
                raise

            log.debug('imported %r' % added)
        else:
            original_filenames = []

        if foreground:
            git_store.post_preparation_hook()
        else:
            git_store.init_progress_preparation()

        return git_store, original_filenames

    @classmethod
    def create_from_tus(
        cls,
        description,
        owner,
        transaction_id,
        paths=[],
        submitter=None,
        foreground=False,
        **kwargs,
    ):
        assert transaction_id is not None
        if owner is not None and not owner.is_anonymous:
            git_store_owner = owner
        else:
            git_store_owner = User.get_public_user()
        git_store = cls(
            major_type=GitStoreMajorType.filesystem,
            description=description,
            owner_guid=git_store_owner.guid,
            **kwargs,
        )

        if submitter:
            git_store.submitter = submitter

        with db.session.begin(subtransactions=True):
            db.session.add(git_store)

        log.info('created %r' % git_store)
        added = None
        try:
            added, original_filenames = git_store.import_tus_files(
                transaction_id=transaction_id, paths=paths, foreground=foreground
            )
        except Exception:  # pragma: no cover
            log.exception(
                'create_from_tus() had problems with import_tus_files(); deleting from db and fs %r'
                % git_store
            )
            git_store.delete()
            raise

        if foreground:
            git_store.post_preparation_hook()
        else:
            git_store.init_progress_preparation()

        log.info('imported %r' % added)
        return git_store, original_filenames

    def import_tus_files(
        self, transaction_id=None, paths=None, foreground=False, purge_dir=True
    ):
        from app.extensions.tus import tus_filepaths_from, tus_purge

        self.ensure_repository()

        sub_id = None if transaction_id is not None else self.guid
        local_store_path = self.get_absolute_path()
        local_name_path = os.path.join(local_store_path, '_uploads')
        local_metadata_path = os.path.join(local_store_path, '_metadata')

        filepaths, metadatas = tus_filepaths_from(
            git_store_guid=sub_id, transaction_id=transaction_id, paths=paths
        )
        uploaded_files = [meta['filename'] for meta in metadatas]
        if paths:
            unprocessed_files = [
                filename for filename in uploaded_files if filename not in paths
            ]
            if unprocessed_files:
                raise HoustonException(log, f'Asset(s) {unprocessed_files} are not used')

        paths_added = []
        original_filenames = []
        for path, metadata in zip(filepaths, metadatas):
            name = pathlib.Path(path).name
            paths_added.append(name)
            os.rename(path, os.path.join(local_name_path, name))
            original_filename = metadata.get('filename', None)
            original_filenames.append(original_filename)

            filename = metadata.get('filename', None)
            if filename is not None:
                metadata_filepath = os.path.join(
                    local_metadata_path, '%s.metadata.json' % (name,)
                )
                with open(metadata_filepath, 'w') as metadata_file:
                    metadata_ = {
                        'filename': filename,
                    }
                    json.dump(metadata_, metadata_file)

        assets_added = []
        num_files = len(paths_added)
        if num_files > 0:
            log.debug('Tus collect for %d files moved' % (num_files))
            self.git_commit(
                'Tus collect commit for %d files.' % (num_files,),
                input_filenames=original_filenames,
                update=foreground,
                commit=foreground,
            )

            # Do git push to gitlab in the background (we won't wait for its
            # completion here)
            self.git_push_delay()

            for asset in self.assets:
                if asset.path in paths_added:
                    assets_added.append(asset)

        if purge_dir:
            # may have some unclaimed files in it
            tus_purge(git_store_guid=sub_id, transaction_id=transaction_id)

        return assets_added, original_filenames

    def realize_local_store(self):
        """
        Unpack any archives and resolve any symlinks

        Must check for security vulnerabilities around decompression bombs and
        recursive links
        """
        ARCHIVE_MIME_TYPE_WHITELIST = [  # NOQA
            'application/gzip',
            'application/vnd.rar',
            'application/x-7z-compressed',
            'application/x-bzip',
            'application/x-bzip2',
            'application/x-tar',
            'application/zip',
        ]
        pass

    def update_asset_symlinks(
        self, existing_filepath_guid_mapping={}, input_filenames=[]
    ):
        """
        Traverse the files in the _raw/ folder and add/update symlinks
        for any relevant files we identify

        This function represents Step 3 in self.git_commit().
        The progress domain for this function is Percentage: 89% (1% -> 90%)

        Ref:
            https://pypi.org/project/python-magic/
            https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
            http://www.iana.org/assignments/media-types/media-types.xhtml
        """
        assets = []

        try:
            assert self.exists

            import utool as ut
            import magic

            # Step 3.1
            #   Description: Walk the files in the repo and extract the Magic signatures and file stats
            #   Delay: a small overhead, should still be relatively quicklatively, unbounded seconds (Step 3.1 << Step 3.2)
            #   Percentage: 1 - 10%

            local_store_path = self.get_absolute_path()
            local_name_path = os.path.join(local_store_path, '_uploads')
            local_assets_path = os.path.join(local_store_path, '_assets')

            # Walk the local store path, looking for white-listed MIME type files
            files = []
            skipped = []
            errors = []
            walk_list = sorted(list(os.walk(local_name_path)))
            for root, directories, filenames in walk_list:
                filenames = sorted(filenames)

                if len(directories) > 0:
                    log.warning(
                        'Skipping import of %d directories found in %r'
                        % (
                            len(directories),
                            root,
                        )
                    )

                for filename in tqdm.tqdm(filenames, desc='Walking Assets'):
                    filepath = os.path.join(root, filename)

                    # Normalize path (sanity check)
                    filepath = os.path.normpath(filepath)

                    # Sanity check, ensure that the path is formatted well
                    assert os.path.exists(filepath)
                    assert os.path.isabs(filepath)
                    try:
                        basename = os.path.basename(filepath)
                        _, extension = os.path.splitext(basename)
                        extension = extension.lower()
                        extension = extension.strip('.')

                        if basename.startswith('.'):
                            # Skip hidden files
                            if basename not in ['.touch']:
                                skipped.append((filepath, basename))
                            continue

                        if os.path.isdir(filepath):
                            # Skip any directories (sanity check)
                            skipped.append((filepath, extension))
                            continue

                        if os.path.islink(filepath):
                            # Skip any symbolic links (sanity check)
                            skipped.append((filepath, extension))
                            continue
                        mime_type = magic.from_file(filepath, mime=True)
                        if mime_type not in self.mime_type_whitelist:
                            # Skip any unsupported MIME types
                            skipped.append((filepath, extension))
                            continue

                        magic_signature = magic.from_file(filepath)
                        size_bytes = os.path.getsize(filepath)

                        this_input_filename = None
                        for input_filename in input_filenames:
                            from app.utils import get_stored_filename

                            if get_stored_filename(input_filename) == basename:
                                this_input_filename = input_filename
                                break

                        file_data = {
                            'filepath': filepath,
                            'path': this_input_filename
                            if this_input_filename
                            else basename,
                            'mime_type': mime_type,
                            'magic_signature': magic_signature,
                            'size_bytes': size_bytes,
                            'git_store_guid': self.guid,
                        }

                        files.append(file_data)
                    except Exception:  # pragma: no cover
                        logging.exception('Got exception in update_asset_symlinks')
                        errors.append(filepath)

            log.info('Processed asset files from: %r' % (self,))
            log.info('\tFiles   : %d' % (len(files),))
            log.info('\tSkipped : %d' % (len(skipped),))
            if len(skipped) > 0:
                skipped_ext_list = [skip[1] for skip in skipped]
                skipped_ext_str = ut.repr3(ut.dict_hist(skipped_ext_list))
                skipped_ext_str = skipped_ext_str.replace('\n', '\n\t\t')
                log.info('\t\t%s' % (skipped_ext_str,))
            log.info('\tErrors  : %d' % (len(errors),))

            if self.progress_preparation:
                self.progress_preparation.set(10)

            # Step 3.2
            #   Description: Compute the xxHash64 values for all of the found files
            #   Delay: major pre-compute step, unbounded seconds (Step 3.2 < Step 3.4)
            #   Percentage: 9% (10% -> 19%)
            assert self.exists

            # Compute the xxHash64 for all found files
            filepath_list = [file_data_['filepath'] for file_data_ in files]
            arguments_list = list(zip(filepath_list))
            log.info('Computing filesystem xxHash64...')
            filesystem_xxhash64_list = parallel(
                compute_xxhash64_digest_filepath, arguments_list
            )
            filesystem_guid_list = list(
                map(ut.hashable_to_uuid, filesystem_xxhash64_list)
            )

            if self.progress_preparation:
                self.progress_preparation.set(19)

            # Step 3.3
            #   Description: Prepare metadata for adding the Assets to the DB, clean up any existing symlinks
            #   Delay: a small overhead, should still be relatively quicklatively, unbounded seconds (Step 3.3 << Step 3.4)
            #   Percentage: 1% (19% -> 20%)
            assert self.exists

            # Update file_data with the filesystem and semantic hash information
            zipped = zip(files, filesystem_xxhash64_list, filesystem_guid_list)
            for file_data, filesystem_xxhash64, filesystem_guid in zipped:
                file_data['filesystem_xxhash64'] = filesystem_xxhash64
                file_data['filesystem_guid'] = filesystem_guid

                semantic_guid_data = [
                    file_data['git_store_guid'],
                    file_data['filesystem_guid'],
                ]
                file_data['semantic_guid'] = ut.hashable_to_uuid(semantic_guid_data)

            # Delete all existing symlinks
            existing_asset_symlinks = ut.glob(os.path.join(local_assets_path, '*'))
            for existing_asset_symlink in existing_asset_symlinks:
                basename = os.path.basename(existing_asset_symlink)
                if basename in ['.touch', '_derived']:
                    continue
                existing_asset_target = os.readlink(existing_asset_symlink)
                existing_asset_target_ = os.path.abspath(
                    os.path.join(local_assets_path, existing_asset_target)
                )
                if os.path.exists(existing_asset_target_):
                    uuid_str, _ = os.path.splitext(basename)
                    uuid_str = uuid_str.strip().strip('.')
                    if existing_asset_target_ not in existing_filepath_guid_mapping:
                        try:
                            existing_filepath_guid_mapping[
                                existing_asset_target_
                            ] = uuid.UUID(uuid_str)
                        except Exception:
                            pass
                os.remove(existing_asset_symlink)

            if self.progress_preparation:
                self.progress_preparation.set(20)

            # Step 3.4
            #   Description: Add the assets to the database
            #   Delay: the majority of the processing, unbounded seconds
            #   Percentage: 60% (20% -> 80%)
            assert self.exists

            # Add new or update any existing Assets found in the Git Store
            local_asset_filepath_list = [
                file_data.pop('filepath', None) for file_data in files
            ]
            # TODO: slim down this DB context
            with db.session.begin(subtransactions=True):
                zipped = list(zip(files, local_asset_filepath_list))
                for index, zip_data in enumerate(zipped):
                    assert self.exists

                    file_data, local_asset_filepath = zip_data

                    semantic_guid = file_data.get('semantic_guid', None)
                    asset = Asset.query.filter(
                        Asset.semantic_guid == semantic_guid
                    ).first()
                    if asset is None:
                        # Check if we can recycle existing GUID from symlink
                        recycle_guid = existing_filepath_guid_mapping.get(
                            local_asset_filepath, None
                        )
                        if recycle_guid is not None:
                            file_data['guid'] = recycle_guid

                        # Create record if asset is new
                        asset = Asset(**file_data)
                        db.session.add(asset)
                    else:
                        # Update record if Asset exists
                        search_keys = [
                            'filesystem_guid',
                            'semantic_guid',
                            'git_store_guid',
                        ]

                        for key in file_data:
                            if key in search_keys:
                                continue
                            value = file_data[key]
                            setattr(asset, key, value)
                        db.session.merge(asset)
                    assets.append(asset)

                    if self.progress_preparation:
                        numerator = index
                        denominator = len(zipped)
                        percentage = numerator / denominator
                        offset = 20.0
                        domain = 60.0
                        new_percentage = offset + (domain * percentage)
                        new_percentage = max(offset, min(offset + domain, new_percentage))
                        self.progress_preparation.set(new_percentage)

            if self.progress_preparation:
                self.progress_preparation.set(80)

            # Step 3.5
            #   Description: Reload all of the assets into memory and update their symlinks
            #   Delay: the majority of the processing, unbounded seconds
            #   Percentage: 9% (89% -> 89%)
            assert self.exists

            # Update all symlinks for each Asset
            for asset, local_asset_filepath in zip(assets, local_asset_filepath_list):
                db.session.refresh(asset)
                asset.update_symlink(local_asset_filepath)
                asset.set_derived_meta()

                log.debug(filepath)
                log.debug('\tAsset         : %s' % (asset,))
                log.debug('\tSemantic GUID : %s' % (asset.semantic_guid,))
                log.debug('\tMIME type     : %s' % (asset.mime_type,))
                log.debug('\tSignature     : %s' % (asset.magic_signature,))
                log.debug('\tSize bytes    : %s' % (asset.size_bytes,))
                log.debug('\tFS xxHash64   : %s' % (asset.filesystem_xxhash64,))
                log.debug('\tFS GUID       : %s' % (asset.filesystem_guid,))

            # Get all historical and current Assets for this Git Store
            assert self.exists
            db.session.refresh(self)

            if self.progress_preparation:
                self.progress_preparation.set(89)
        except Exception:
            if self.progress_preparation:
                self.progress_preparation.fail()
            raise
        finally:
            if not self.exists:
                # Delete all assets that were added during this session
                deleted_assets = assets
            else:
                # Figure out what Assets we need to delete because they aren't on disk anymore
                deleted_assets = list(set(self.assets) - set(assets))

        # Step 3.6
        #   Description: Cleanup of any deleted assets
        #   Delay: small overhead, unbounded seconds
        #   Percentage: 1% (89% -> 90%)

        # Delete any historical Assets that have been deleted from this commit
        log.info('Deleting %d orphaned Assets' % (len(deleted_assets),))
        for deleted_asset in deleted_assets:
            with db.session.begin(subtransactions=True):
                try:
                    if deleted_asset.exists:
                        deleted_asset.delete()
                except Exception:
                    pass

        assert self.exists
        db.session.refresh(self)

        if self.progress_preparation:
            self.progress_preparation.set(90)

    def update_metadata_from_project(self, project):
        # Update any local metadata from sub
        for tag in project.tag_list:
            tag = tag.strip().split(':')
            if len(tag) == 2:
                key, value = tag
                key_ = key.lower()
                value_ = value.lower()
                if key_ == 'type':
                    default_major_type = GitStoreMajorType.unknown
                    self.major_type = getattr(
                        GitStoreMajorType, value_, default_major_type
                    )

        self.description = project.description
        with db.session.begin():
            db.session.merge(self)
        db.session.refresh(self)

    def update_metadata_from_repo(self, repo):
        repo = self.get_repository()
        assert repo is not None

        if len(repo.branches) > 0:
            commit = repo.branches.master.commit
            self.update_metadata_from_commit(commit)

        return repo

    def update_metadata_from_commit(self, commit):
        self.commit = commit.hexsha

        metadata_path = os.path.join(commit.repo.working_dir, 'metadata.json')
        assert os.path.exists(metadata_path)
        with open(metadata_path, 'r') as metadata_file:
            metadata_dict = json.load(metadata_file)

        self.commit_mime_whitelist_guid = metadata_dict.get(
            'commit_mime_whitelist_guid', self.mime_type_whitelist_guid
        )
        self.commit_houston_api_version = metadata_dict.get(
            'commit_houston_api_version', version
        )

        with db.session.begin(subtransactions=True):
            db.session.merge(self)
        db.session.refresh(self)

    def update_metadata_from_hook(self):
        local_store_path = self.get_absolute_path()
        local_store_metadata_path = os.path.join(local_store_path, 'metadata.json')

        assert os.path.exists(local_store_metadata_path)
        with open(local_store_metadata_path, 'r') as local_store_metadata_file:
            local_store_metadata = json.load(local_store_metadata_file)

        self.git_commit_metadata_hook(local_store_metadata)

        with open(local_store_metadata_path, 'w') as local_store_metadata_file:
            json.dump(local_store_metadata, local_store_metadata_file)

    def get_absolute_path(self):
        local_database_path = current_app.config.get(
            self.GIT_STORE_DATABASE_PATH_CONFIG_NAME, None
        )
        assert local_database_path is not None
        assert os.path.exists(local_database_path)

        local_store_path = os.path.join(local_database_path, str(self.guid))

        return local_store_path

    def delete_dirs(self):
        if os.path.exists(self.get_absolute_path()):
            shutil.rmtree(self.get_absolute_path())

    def get_asset_for_file(self, filename):
        for asset in self.assets:
            if asset.path == filename:
                return asset
        return None

    # stub of DEX-220 ... to be continued
    def justify_existence(self):
        if self.assets:  # we have assets, so we live on
            return
        log.warning('justify_existence() found ZERO assets, self-destructing %r' % self)
        self.delete()  # TODO will this also kill remote repo?

    def get_repository(self):
        repo_path = pathlib.Path(self.get_absolute_path())
        if (repo_path / '.git').exists():
            return Repo(repo_path)

    def ensure_repository(self):
        from app.extensions.elapsed_time import ElapsedTime

        timer = ElapsedTime()
        repo = self.get_repository()
        if repo:
            if 'origin' in repo.remotes:
                repo = self.git_pull()
        else:
            cls = type(self)
            project = cls.get_remote(self.guid)
            if project:
                repo = self.git_clone(project)
            else:
                repo = Repo.init(self.get_absolute_path())
        self._ensure_repository_files()

        if float(timer.elapsed()) > 0.05:
            log.info(
                f'Ensure Git repository for Git Store {self.guid} took {timer.elapsed()} seconds'
            )
        return repo

    @classmethod
    def get_remote(cls, guid):
        from app.extensions.gitlab import GitlabInitializationError

        try:
            return current_app.git_backend.get_project(str(guid))
        except (
            GitlabInitializationError,
            requests.exceptions.RequestException,
        ):  # pragma: no cover
            log.exception(f'Error when calling git store get_remote({guid})')

    @classmethod
    def is_on_remote(cls, guid):
        from app.extensions.gitlab import GitlabInitializationError

        try:
            return current_app.git_backend.is_project_on_remote(str(guid))
        except (
            GitlabInitializationError,
            requests.exceptions.RequestException,
        ):  # pragma: no cover
            log.exception(f'Error when calling git store is_on_remote({guid})')
            return False

    def delete(self):
        additional = []

        if self.progress_preparation:
            additional.append(self.progress_preparation)

        with db.session.begin(subtransactions=True):
            for asset in self.assets:
                asset.delete_cascade()
        # TODO: This is potentially dangerous as it decouples the Asset deletion
        #       transaction with the AssetGroup deletion transaction, bad for rollbacks
        with db.session.begin(subtransactions=True):
            db.session.delete(self)

        with db.session.begin(subtransactions=True):
            for obj in additional:
                obj.delete()

        self.delete_dirs()

        # Delete the gitlab project in the background (we won't wait
        # for its completion)
        self.delete_remote_delay()
