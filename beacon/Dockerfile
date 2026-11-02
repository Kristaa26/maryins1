# Beacon — MaryLab machine (Docker, VM-style single host).
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

# --- base packages ---------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-pip \
        nginx \
        postgresql postgresql-client \
        openssh-server \
        cron \
        git \
        sudo \
        procps iproute2 iputils-ping net-tools \
        curl ca-certificates vim-tiny less \
        tini \
    && rm -rf /var/lib/apt/lists/*

# --- python venv for the web apps -----------------------------------------
COPY build/requirements.txt /opt/beacon/requirements.txt
RUN python3 -m venv /opt/beacon/venv \
    && /opt/beacon/venv/bin/pip install --no-cache-dir -r /opt/beacon/requirements.txt

# --- users -----------------------------------------------------------------
# beacon-ops: service account that runs the site + Ops Console (foothold).
# maya:       release-deploy automation account (user-flag account).
RUN useradd -u 1001 -M -d /opt/beacon -s /usr/sbin/nologin beacon-ops \
    && useradd -u 1100 -m -s /bin/bash maya \
    && echo 'maya:Beacon-Deploy-7F2a!' | chpasswd \
    && printf 'root:%s\n' "$(head -c16 /dev/urandom | base64 | tr -dc A-Za-z0-9 | head -c20)" | chpasswd

# --- application code ------------------------------------------------------
COPY src/marketing  /opt/beacon/site
COPY src/repoforge  /opt/beacon/repoforge
COPY build/run/site-run.sh   /opt/beacon/site/run.sh
COPY build/run/forge-run.sh  /opt/beacon/repoforge/run.sh
COPY build/maintenance/reset_sandbox.sh /opt/beacon/maintenance/reset_sandbox.sh
COPY build/maintenance/beacon-ops.cron  /opt/beacon/maintenance/beacon-ops.cron
COPY build/beacon.env        /etc/beacon/beacon.env
COPY build/entrypoint.sh     /usr/local/bin/entrypoint.sh
COPY seed/build_repos.sh     /opt/beacon/seed/build_repos.sh

RUN chmod +x /opt/beacon/site/run.sh /opt/beacon/repoforge/run.sh \
        /opt/beacon/maintenance/reset_sandbox.sh \
        /usr/local/bin/entrypoint.sh /opt/beacon/seed/build_repos.sh

# --- logs & env perms ------------------------------------------------------
RUN mkdir -p /var/log/beacon \
    && touch /var/log/beacon/probe.log /var/log/beacon/reset.log \
             /var/log/beacon/site.access.log /var/log/beacon/site.error.log \
             /var/log/beacon/forge.access.log /var/log/beacon/forge.error.log \
    && chown -R beacon-ops:beacon-ops /var/log/beacon \
    && chown www-data:www-data /var/log/beacon/forge.access.log /var/log/beacon/forge.error.log \
    && chown root:beacon-ops /etc/beacon/beacon.env && chmod 640 /etc/beacon/beacon.env \
    && chown -R beacon-ops:beacon-ops /opt/beacon/maintenance

# --- seed RepoForge repositories ------------------------------------------
RUN /opt/beacon/seed/build_repos.sh /srv/repoforge/repos \
    && chown -R www-data:www-data /srv/repoforge

# --- release download placeholders ----------------------------------------
RUN mkdir -p /var/www/dl \
    && for f in beacon-2.7.0-linux-amd64 beacon-2.7.0-linux-arm64 beacon-2.7.0-darwin-arm64; do \
         echo "Beacon v2.7.0 release artifact placeholder ($f). Build from source: git.beacon.myl/lumen-systems/beacon" \
           | gzip -c > /var/www/dl/$f.tar.gz; \
       done

# --- nginx -----------------------------------------------------------------
COPY build/nginx/beacon.conf /etc/nginx/sites-available/beacon.conf
RUN rm -f /etc/nginx/sites-enabled/default \
    && ln -sf /etc/nginx/sites-available/beacon.conf /etc/nginx/sites-enabled/beacon.conf

# --- postgres: create db/role, load schema+seed, allow password auth ------
COPY build/db/schema.sql /opt/beacon/db/schema.sql
COPY build/db/seed.sql   /opt/beacon/db/seed.sql
COPY build/db/grants.sql /opt/beacon/db/grants.sql
RUN PGVER="$(ls /etc/postgresql)" \
    && HBA="/etc/postgresql/$PGVER/main/pg_hba.conf" \
    && echo "host    all    all    127.0.0.1/32    md5" >> "$HBA" \
    && echo "host    all    all    ::1/128         md5" >> "$HBA" \
    && pg_ctlcluster "$PGVER" main start \
    && su postgres -c "psql -v ON_ERROR_STOP=1 -c \"CREATE DATABASE beacon;\"" \
    && su postgres -c "psql -v ON_ERROR_STOP=1 -d beacon -f /opt/beacon/db/schema.sql" \
    && su postgres -c "psql -v ON_ERROR_STOP=1 -d beacon -f /opt/beacon/db/seed.sql" \
    && su postgres -c "psql -v ON_ERROR_STOP=1 -d beacon -f /opt/beacon/db/grants.sql" \
    && pg_ctlcluster "$PGVER" main stop

# --- flags -----------------------------------------------------------------
RUN echo '014dedcc0de6f769801aa5c8117be764' > /home/maya/user.txt \
    && chown root:maya /home/maya/user.txt && chmod 640 /home/maya/user.txt \
    && echo '6d66ce112a162d9911717305f5a38c39' > /root/root.txt \
    && chown root:root /root/root.txt && chmod 640 /root/root.txt

# --- sudo misconfiguration (maya may back up as root via tar) --------------
RUN echo '# maya runs the nightly site/config backup as root' > /etc/sudoers.d/maya \
    && echo 'maya ALL=(root) NOPASSWD: /usr/bin/tar' >> /etc/sudoers.d/maya \
    && chmod 440 /etc/sudoers.d/maya \
    && visudo -cf /etc/sudoers.d/maya

# --- sshd ------------------------------------------------------------------
RUN sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
    && printf '\n# Beacon lab\nAllowUsers maya\n' >> /etc/ssh/sshd_config \
    && ssh-keygen -A

# --- install the beacon-ops resetter crontab -------------------------------
RUN crontab -u beacon-ops /opt/beacon/maintenance/beacon-ops.cron

EXPOSE 22 80
ENTRYPOINT ["/usr/bin/tini","--","/usr/local/bin/entrypoint.sh"]
