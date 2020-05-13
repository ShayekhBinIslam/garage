import subprocess

from fabric import Connection


def get_root_path():
    git_root_path = subprocess.check_output(
        ('git', 'rev-parse', '--show-toplevel'), stderr=subprocess.DEVNULL)
    return git_root_path.decode('utf-8').strip()


def make_launcher_archive(git_root_path):
    """Saves an archive of the launcher's git repo to the log directory.

    Args:
        git_root_path (str): Absolute path to git repo to archive.

    """
    files_to_archive = subprocess.check_output(
        ('git', 'ls-files', '--others', '--exclude-standard', '--cached',
         '-z'),
        cwd=git_root_path).strip()
    archive_path = 'launch_archive.tar.xz'
    subprocess.run(('tar', '--null', '--files-from', '-', '--auto-compress',
                    '--create', '--file', archive_path),
                   input=files_to_archive,
                   cwd=git_root_path,
                   check=True)


def distribute(config, exp_name_suffix, connect_kwargs):
    git_root_path = get_root_path()
    make_launcher_archive(git_root_path)
    remote_dir = f'garage_exp_{exp_name_suffix}'
    for host, exp in config.items():
        print(f'Connecting to {host}')
        c = Connection(host=host, connect_kwargs=connect_kwargs)
        c.run(f'mkdir {remote_dir}', hide='out', echo=True)
        c.put(f'{git_root_path}/launch_archive.tar.xz', remote=remote_dir)
        c.run(
            'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/.mujoco/mujoco200/bin'
        )
        with c.prefix(
                'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/.mujoco/mujoco200/bin'
        ):
            with c.cd(remote_dir):
                c.run(f'tar -xf launch_archive.tar.xz', hide='out', echo=True)
                c.run(f'python3 -m venv garage_venv', hide='out', echo=True)
                c.run(f'pip3 install .[all]', hide='out', echo=True)
                c.run(f'pip3 install .[dev]', hide='out', echo=True)
                c.run(f'tmux new -d -s {remote_dir}', hide='out', echo=True)
                c.run(f'tmux send-keys -t {remote_dir} ./{exp} ENTER',
                      hide='out',
                      echo=True)
