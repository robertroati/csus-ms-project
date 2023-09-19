# Pre-Incident Forensics Data Capture

## Table of Contents
- [Console](#console)
- [Service](#service)
- [Configuration](#configuration)

## Console

- Provides access to service and its functions.
- Doesn't require elevated privileges.
- Requires password authentication to access service functions.
- Authenticated sessions timeout after configured idle time.
- Provides the ability to:
  - Modify configuration, including changing console password.
  - Display monitored files and commands.
  - Display change history for monitored files and commands.
  - Add files and commands to be monitored.
  - Toggle monitoring on/off for existing files and commands.
  - Display catalog of detected processes.
  - Add detected process to the approved list for baseline.
  - Display catalog of detected devices.
  - Add detected device to the approved list for baseline.

## Service

- Multi-threaded: Service functions are separate from client communications.
- SSL socket communication provides easy migration to client/server environment.
- Uses encrypted local database (SQLite3), with easy migration to client/server environment.
- Provides:
  - Syslog/SIEM notifications (with meaningful levels: info, error, warning, critical)
  - SFTP uploads of logs and/or service database.
  - Baseline monitoring of specified files.
  - Baseline monitoring of specified commands. Supports piped commands.
  - Captures and logs shell commands made by users.
  - Monitoring of attached devices, with baseline approval for each device.
  - Monitoring of running processes, with baseline approval for each device.
  - The ability to capture PCAPs of network interfaces.
  - When told to lock-down, the system will:
    - Disconnect logged-in users.
    - Upload service database and logs to configured SFTP server.
    - Disable all user accounts.
    - Create a new user (specified by config).
    - Disable Ethernet interfaces.

## Configuration

The initial configuration is provided via a JSON config file and is consumed after import.

### Options

- SME contact data (shown on locked MOTD and on console login screen)
- Host system ID, console password (plaintext), console timeout, system unlock username, and password (plaintext)
- SFTP Server connection information: host/port/username/password
- SIEM/Syslog host information: host, port
- Initial list of commands to monitor.
- Initial list of files to monitor.
- Enable PCAP collections.
- PCAP collection interval.
- Number of PCAPs to store.
- A list of comma-delimited interface names to capture.
- Various intervals for service checks.