#!/usr/bin/env python3
"""Upload a single local file to remote via `cat > remote` over an exec channel + stdin.
Avoids SFTP (autodl SFTP subsystem appears write-restricted). Password from SSH_PASS env.
Usage: SSH_PASS=xxx python ssh_upload.py <local_file> <remote_file>
"""
import os
import sys
import shlex
import paramiko

HOST = "connect.bjb1.seetacloud.com"
PORT = 38038
USER = "root"


def main():
    if len(sys.argv) < 3:
        sys.stderr.write("usage: ssh_upload.py <local_file> <remote_file>\n"); sys.exit(2)
    local, remote = sys.argv[1], sys.argv[2]
    remote = remote.replace("\\", "/")
    passwd = os.environ.get("SSH_PASS")
    if not passwd:
        sys.stderr.write("ERROR: SSH_PASS env not set\n"); sys.exit(2)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=passwd, timeout=30)

    dirname = os.path.dirname(remote)
    cmd = f"mkdir -p {shlex.quote(dirname)} && cat > {shlex.quote(remote)}"
    chan = client.get_transport().open_session()
    chan.exec_command(cmd)
    with open(local, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            chan.sendall(chunk)
    chan.shutdown_write()
    rc = chan.recv_exit_status()
    err = b""
    while chan.recv_stderr_ready():
        err += chan.recv_stderr(4096)
    client.close()
    print(f"upload {local} -> {remote} (rc={rc}, {os.path.getsize(local)} bytes)")
    if err:
        sys.stderr.write(err.decode("utf-8", "replace"))
    sys.exit(rc)


if __name__ == "__main__":
    main()
