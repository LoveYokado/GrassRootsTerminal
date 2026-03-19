# GrassRootsBBS

`GrassRootsTerminal` is a web-based terminal gateway extracted from `GrassRootsBBS`, a system designed to recreate the nostalgic experience of 1990s PC communication (BBS) using modern technology. It functions as a standalone gateway dedicated to providing a classic terminal interface.

## Project Background

In the 1990s, the BBS scene was a "warring states period" of diverse host programs—`WWIV`, `Big-Model`, `RTBBS`, `mmm`, and many others. I spent much of my time connected to various boards, centered around `Big-Model` sites. Each BBS had its own unique personality, and Sysops would carefully choose the host program that best fit their vision from the many options available.

However, in the modern era, very few of these host programs have survived, and BBSs that operate with a native WebUI are even rarer.

`GrassRootsTerminal` was created to bridge this gap. By utilizing the Telnet protocol, which is still the standard for many surviving host programs, I aimed to recreate the authentic BBS experience as faithfully as possible for today’s users. This project is the standalone terminal component of `GrassRootsBBS`, redesigned to bring the soul of the 90s terminal era to the modern web.

## Support the Project ☕

`GrassRootsTerminal` is essentially a fork of the original `GrassRootsBBS` project. If you enjoy using this software and would like to support the ongoing development of `GrassRootsBBS`, I would be incredibly grateful if you could buy me a coffee!

Your warm support serves as a vital energy source for me, providing the motivation needed for continuous development and long-term maintenance. Thank you for being part of this journey!

[![Support me on Ko-fi](https://img.shields.io/badge/Support%20me%20on%20Ko--fi-F16061?logo=ko-fi&logoColor=white)](https://ko-fi.com/loveyokado)
[Support me on Ko-fi](https://ko-fi.com/loveyokado)

## Main Features

- **Retro-Modern Web Terminal UI:**
  - **Customizable Themes & Fonts:** Choose your favorite look, including classic Green Monitor and Amber Monitor styles.

  - **Multilingual Support:** Ready for English and Japanese, with an extensible design to support additional languages.

  - **Playful Hardware Emulation:** A unique settings screen featuring functional, interactive DIP switches.

  - **PWA Ready:** Installable on smartphones as a Progressive Web App for a native-like experience.

- **Simple Telnet Gateway:**
  - **Easy Setup:** Get up and running quickly with Docker Compose.

  - **Seamless Configuration:** Works instantly by simply specifying your Telnet port in the configuration file.

## Installation & Setup

**Prerequisites:** Docker, Docker Compose

### 1. Clone the Repository

```bash
git clone https://github.com/LoveYokado/grassrootsterminal.git
cd GrassRootsTerminal
```

### 2. Environment Variables

Copy the `.env.example` file to `.env` file, and edit the contents to match your environment.

```bash
cp .env.example .env
```

Most settings should work fine with the default values.

### 3. Edit Configuration Files

Copy the config.toml.example file to create your config.toml, then edit it as needed:

```bash
cp setting/config.toml.example setting/config.toml
```

```toml
[telnet]
host = "sbbs"    # In a Docker Compose environment, use the service name (e.g., "sbbs").
port = 23        # The Telnet port of your BBS.
timeout = 300    # Terminal session timeout in seconds.
[webapp]
ORIGIN = "http://localhost:5000" # The full URL used to access the terminal (including protocol, host, and port).
```

### 4. PWA Manifest Settings

Set the app name and icons for PWA installation. Copy manifest.json.example to manifest.json and edit if necessary.

```bash
cp static/manifest.json.example static/manifest.json
```

If you want to change the BBS name, modify the name and short_name fields inside `manifest.json`.

### 5. Launch the Server

Copy the Docker Compose example file:

```bash
cp docker-compose.yml.example docker-compose.yml
```

In the provided sample, `Synchronet` (the host program for Synchronet BBS) is included but commented out. Please uncomment the relevant sections to enable the service as needed.

You can also support other host programs by adding similar service definitions, provided they are compatible with the Telnet protocol.

Start the BBS using Docker Compose:

```bash
docker-compose up --build -d
```

### 6. Accessing the BBS

Access the BBS in your browser at `http://localhost:5000`.

### 7. (Optional) Production Deployment: Nginx Reverse Proxy

For public internet deployment, we recommend using Nginx as a reverse proxy for security and SSL (HTTPS).

#### a. Prepare Nginx Configuration

Copy the example configuration:

```bash
cp nginx.config.example nginx.conf
```

Open `nginx.conf` and edit the sections marked TODO:

- `server_name`: Change `example.com` to your domain.
- SSL Certificate Paths: Specify the correct paths to your SSL certificate and private key (e.g., from Let's Encrypt).

#### b. Obtain SSL Certificates (via Let's Encrypt)

You can use Certbot to obtain free certificates:

```bash
# Replace 'your_domain' and email address
sudo certbot certonly --standalone -d your_domain --email your_email@example.com
```

Once obtained, ensure the `ssl_certificate` and `ssl_certificate_key` paths in `nginx.conf` are correct.

## License

This project is licensed under the **GNU General Public License v2.0 (GPLv2)**.

- **Synchronet BBS Software:** Copyright (c) Rob Swindell. Licensed under GPL/LGPL.
- **Docker Configurations & Setup Scripts:** Copyright (c) 2026 LoveYokado. Licensed under GPLv2.
