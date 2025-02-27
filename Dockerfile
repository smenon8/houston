FROM node:lts as swagger-ui
# Copy the necessary source items
RUN mkdir /code
COPY ./_swagger-ui /code/_swagger-ui
COPY ./scripts /code/scripts
# Build the frontend
RUN set -x \
    && cd /code \
    && ls -lah \
    && export DEBUG=1 \
    && /bin/bash -c "source ./scripts/swagger/build.sh && build" \
    && /bin/bash -c "source ./scripts/swagger/build.sh && install"


FROM python:3.9 as main

RUN apt update \
 # && curl -sL https://deb.nodesource.com/setup_14.x | bash - \
 && apt update \
 && apt upgrade -y \
 && apt install -y \
        # Build
        build-essential \
        musl-dev \
        gcc \
        libffi-dev \
        # Python 3
        python3-dev \
        # Convenience
        htop \
        tmux \
        vim \
        git \
        jq \
        # Magic with python-magic (MIME-type parser)
        libmagic1 \
        #: tool to setuid+setgid+setgroups+exec at execution time
        gosu \
        # Needed for profiling
        graphviz \
        #: required by wait-for
        netcat \
        #: required for downloading 'wait-for'
        curl \
 && rm -rf /var/lib/apt/lists/*

# Install wait-for
RUN set -x \
    && curl -s https://raw.githubusercontent.com/eficode/wait-for/v2.0.0/wait-for > /usr/local/bin/wait-for \
    && chmod a+x /usr/local/bin/wait-for \
    # test it works
    && wait-for google.com:80 -- echo "success"

ENV SWAGGER_UI_DIST /var/www/swagger-ui

COPY . /code
RUN ls -lah /code/app/static
COPY --from=swagger-ui /code/app/static/swagger-ui ${SWAGGER_UI_DIST}
RUN ls -lah /code/app/static

WORKDIR /code

RUN set -ex \
 && pip install --upgrade pip \
 && pip install -e . \
 #: Install developer tools
 && pip install -r app/requirements.dev.txt \
 #: Remove pip download cache
 && rm -rf ~/.cache/pip

EXPOSE 5000
ENV FLASK_ENV production

# Location to mount our data
ENV DATA_VOLUME /data
# Location the data will be writen to
ENV DATA_ROOT ${DATA_VOLUME}/var
VOLUME [ "${DATA_VOLUME}" ]

# Location to source additional environment variables
ENV HOUSTON_DOTENV ${DATA_ROOT}/.env

COPY ./.dockerfiles/docker-entrypoint.sh /docker-entrypoint.sh
COPY ./.dockerfiles/docker-healthcheck.sh /docker-healthcheck.sh

COPY ./.dockerfiles/embed.sh /bin/embed

ENTRYPOINT [ "/docker-entrypoint.sh" ]
#: default command within the entrypoint
# CMD [ "invoke", "app.run" ]


FROM node:lts as frontend
# only "codex"
ARG PROJECT
# Copy the necessary source items
RUN mkdir /code
COPY ./scripts /code/scripts
# Build the frontend
RUN set -x \
    && cd /code \
    && git clone https://github.com/WildMeOrg/${PROJECT}-frontend.git _frontend.${PROJECT} \
    && export DEBUG=1 \
    && /bin/bash -c "source ./scripts/${PROJECT}/build.frontend.sh && build" \
    && /bin/bash -c "source ./scripts/${PROJECT}/build.frontend.sh && install"


FROM main as with_frontend

ENV FRONTEND_DIST /var/www/frontend
COPY --from=frontend /code/app/static/dist-latest ${FRONTEND_DIST}
