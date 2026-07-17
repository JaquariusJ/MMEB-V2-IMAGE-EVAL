#!/usr/bin/env python3
"""Reusable SSH runner. Password is read from SSH_PASS env var (never hard-coded).
Usage: SSH_PASS=xxx python ssh_run.py "<remote shell command>" [--timeout N] [--pty]
The remote command is wrapped with `bash -lc` so the login shell / conda PATH loads.
"""
import os
import sys
import shlex
import paramiko

HOST = "connect.bjb1.seetacloud.com"
PORT = 38038
USER = "root"


def main():
    args = sys.argv[1:]
    timeout = 120
    pty = False
    positional = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--timeout":
            timeout = int(args[i + 1]); i += 2
        elif a == "--pty":
            pty = True; i += 1
        else:
            positional.append(a); i += 1

    cmd = positional[0] if positional else "echo ok"
    passwd = os.environ.get("SSH_PASS")
    if not passwd:
        sys.stderr.write("ERROR: SSH_PASS env not set\n"); sys.exit(2)

    # Wrap in a login shell so conda/PATH is fully loaded (autodl uses /root/miniconda3).
    full = f"bash -lc {shlex.quote(cmd)}"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=passwd,
                   timeout=30, banner_timeout=30, auth_timeout=30)
    try:
        stdin, stdout, stderr = client.exec_command(full, timeout=timeout, get_pty=pty)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        rc = stdout.channel.recv_exit_status()
        sys.stdout.write(out)
        if err:
            sys.stderr.write(err)
        sys.exit(rc)
    finally:
        client.close()


if __name__ == "__main__":
    main()
