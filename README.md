# CTFd-docker-challenge-plugin

A small plugin to dynamically give the users the ability to run instances of a challenge through docker

## Setup

1. Download the plugin and place in inside CTFd/CTFd/plugins
2. In the CTFd/docker-compose.yml, add a volume to the ctfd container to allow it to use docker
```yml
services:
  ctfd:
    build: .
    user: root
    restart: always
    ports:
      - "8000:8000"
    environment:
      - UPLOAD_FOLDER=/var/uploads
      - DATABASE_URL=mysql+pymysql://ctfd:ctfd@db/ctfd
      - REDIS_URL=redis://cache:6379
      - WORKERS=1
      - LOG_FOLDER=/var/log/CTFd
      - ACCESS_LOG=-
      - ERROR_LOG=-
      - REVERSE_PROXY=true
    volumes:
      - .data/CTFd/logs:/var/log/CTFd
      - .data/CTFd/uploads:/var/uploads
      - .:/opt/CTFd:ro
      - /var/run/docker.sock:/var/run/docker.sock   # <--- This line
    depends_on:
      - db
    networks:
        default:
        internal:
      
    ...
```
3. Run the CTFd instance, and set it up
4. Go to the config page for the plugin at: `/admin/docker_challenges`
5. Fill out the page:
    *  External Gateway <- The IP/domain that external devices can access the CTFd instance from
    *  CA Name <- The Common Authority Name for the VPN client configs to be signed by
6. Press `Save`
7. Press `Spawn VPN` and wait ~1 minute, you can check with the progress by running `docker ps -a` and looking at the current container running `kylemanna/openvpn:2.4`
8. You're done
