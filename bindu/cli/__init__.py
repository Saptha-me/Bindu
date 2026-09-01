"""Bindu CLI — command-line interface for the Bindu framework.

Provides the ``bindu`` command with subcommands:

  - ``bindu serve --grpc``       : start the Bindu core for SDK registration
  - ``bindu serve --script PATH`` : execute a user agent script (the script
    calls ``bindufy()`` itself). Used by ``BoxdRuntimeProvider`` inside the VM.
  - ``bindu deploy <script>``     : package the script's project and deploy it
    via a RuntimeProvider (e.g. ``--runtime=boxd``). Streams VM logs to
    stdout, applies ``--on-exit`` policy on Ctrl-C.
  - ``bindu logs <agent>``        : stream logs from the agent's VM
  - ``bindu shell <agent>``       : open an interactive shell on the agent's VM
"""

import argparse
import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Any

from bindu.utils.logging import get_logger

logger = get_logger("bindu.cli")


def _handle_serve(args: argparse.Namespace) -> None:
    """Handle the ``bindu serve`` command.

    Modes:
      ``--script <path>``: execute a user agent script.
      ``--grpc``:          start the gRPC core for SDK registration.
    """
    if args.script:
        _run_user_script(args.script)
        return

    if not args.grpc:
        print("Error: --grpc or --script required for `bindu serve`")
        print("Usage:")
        print("  bindu serve --grpc [--grpc-port 3774]")
        print("  bindu serve --script <path>")
        sys.exit(1)

    # Import here to avoid loading heavy dependencies on --help
    from bindu.grpc.registry import AgentRegistry
    from bindu.grpc.server import start_grpc_server

    grpc_port = args.grpc_port
    registry = AgentRegistry()

    logger.info(f"Starting Bindu core with gRPC on port {grpc_port}")

    server = start_grpc_server(registry=registry, port=grpc_port)

    def _shutdown(signum: int, frame: object) -> None:
        logger.info("Shutting down gRPC server...")
        server.stop(grace=5)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    server.wait_for_termination()


def _run_user_script(path: str) -> None:
    """Execute the user's agent script in ``__main__`` context."""
    import runpy

    script_path = os.path.abspath(path)
    script_dir = os.path.dirname(script_path)
    sys.path.insert(0, script_dir)
    try:
        runpy.run_path(script_path, run_name="__main__")
    finally:
        try:
            sys.path.remove(script_dir)
        except ValueError:
            pass


async def _handle_logs(agent_name: str, follow: bool = True) -> None:
    """Stream the in-VM agent's stdout/stderr to the host terminal."""
    from bindu.runtime import get_provider
    from bindu.runtime.base import RuntimeHandle

    provider = get_provider("boxd")
    handle = RuntimeHandle(name=agent_name, url="", provider="boxd")
    async for chunk in provider.stream_logs(handle, follow=follow):
        sys.stdout.write(chunk.decode("utf-8", errors="replace"))
        sys.stdout.flush()


async def _handle_shell(agent_name: str) -> None:
    """Open an interactive bash on the agent's VM.

    boxd 0.2.x has no interactive-exec convenience, so bridge the local
    terminal to a tty ``stream_exec`` session by hand: raw mode locally,
    stdin pumped into the stream, merged output pumped to stdout.
    """
    import shutil

    from bindu.runtime.boxd_provider import _get_machine, _make_client

    loop = asyncio.get_event_loop()
    cols, rows = shutil.get_terminal_size()

    async with _make_client() as client:
        machine = await _get_machine(client, agent_name)
        if machine is None:
            sys.exit(f"Error: no boxd machine named {agent_name}")
        stream = client.machines.stream_exec(
            machine.id, command="bash", tty=True, cols=cols, rows=rows
        )
        async with stream:
            if not sys.stdin.isatty():
                # No local tty (piped input, tests): just drain output.
                async for chunk in stream:
                    sys.stdout.buffer.write(chunk)
                    sys.stdout.buffer.flush()
                return

            import termios
            import tty as _tty

            fd = sys.stdin.fileno()
            old_attrs = termios.tcgetattr(fd)

            def _pump_stdin() -> None:
                data = os.read(fd, 4096)
                if data:
                    asyncio.ensure_future(stream.write(data))
                else:
                    asyncio.ensure_future(stream.write_eof())

            def _on_winch() -> None:
                size = shutil.get_terminal_size()
                asyncio.ensure_future(stream.resize(size.columns, size.lines))

            _tty.setraw(fd)
            loop.add_reader(fd, _pump_stdin)
            loop.add_signal_handler(signal.SIGWINCH, _on_winch)
            try:
                async for chunk in stream:
                    sys.stdout.buffer.write(chunk)
                    sys.stdout.buffer.flush()
            finally:
                loop.remove_signal_handler(signal.SIGWINCH)
                loop.remove_reader(fd)
                termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)


def _capture_agent_metadata(script_path: str) -> dict[str, Any]:
    """Run the user's script with ``BINDU_DEPLOY_CAPTURE`` set; read the JSON.

    bindufy() short-circuits when the env var is set, dumping the agent name
    and caller_dir without performing any heavy runtime setup.
    """
    import json
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        capture_path = f.name
    Path(capture_path).write_text("")

    prev = os.environ.get("BINDU_DEPLOY_CAPTURE")
    os.environ["BINDU_DEPLOY_CAPTURE"] = capture_path
    try:
        _run_user_script(script_path)
    finally:
        if prev is None:
            os.environ.pop("BINDU_DEPLOY_CAPTURE", None)
        else:
            os.environ["BINDU_DEPLOY_CAPTURE"] = prev

    raw = Path(capture_path).read_text()
    Path(capture_path).unlink(missing_ok=True)
    if not raw:
        sys.exit(f"Error: {script_path} did not call bindufy() — nothing to deploy")
    return json.loads(raw)


def _build_runtime_dict(args: argparse.Namespace) -> dict[str, Any]:
    """Translate ``bindu deploy`` flags into a RuntimeConfig dict."""
    out: dict[str, Any] = {"provider": args.runtime}
    if args.image:
        out["image"] = args.image
    if args.vcpu is not None:
        out["vcpu"] = args.vcpu
    if args.memory:
        out["memory"] = args.memory
    if args.disk:
        out["disk"] = args.disk
    if args.auto_suspend is not None:
        out["auto_suspend"] = args.auto_suspend
    if args.on_exit:
        out["on_exit"] = args.on_exit
    if args.bindu_version:
        out["bindu_version"] = args.bindu_version
    if args.env:
        env_dict: dict[str, str] = {}
        for kv in args.env:
            if "=" not in kv:
                sys.exit(f"Error: --env value must be KEY=VALUE, got: {kv!r}")
            k, v = kv.split("=", 1)
            env_dict[k] = v
        out["env"] = env_dict
    return out


async def _pipe_logs(provider: Any, handle: Any) -> None:
    """Stream VM logs to host stdout, prefixed with the agent name."""
    prefix = f"[{handle.name}] "
    try:
        async for chunk in provider.stream_logs(handle, follow=True):
            text = chunk.decode("utf-8", errors="replace")
            for line in text.splitlines():
                print(prefix + line, flush=True)
    except Exception as e:
        logger.warning(f"{prefix}log stream ended: {e}")


async def _supervise(provider: Any, handle: Any, runtime_config: Any) -> None:
    """Stream logs, block on SIGINT, then apply the configured on_exit."""
    log_task = asyncio.create_task(_pipe_logs(provider, handle))

    stop = asyncio.Event()
    loop = asyncio.get_event_loop()

    def _on_signal() -> None:
        stop.set()

    try:
        loop.add_signal_handler(signal.SIGINT, _on_signal)
        loop.add_signal_handler(signal.SIGTERM, _on_signal)
    except NotImplementedError:
        pass  # Windows / restricted envs

    try:
        await stop.wait()
    finally:
        log_task.cancel()
        try:
            await log_task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"log streaming task failed: {e}")
        await provider.on_exit(handle, runtime_config.on_exit)


def _print_dry_run(
    *,
    agent_name: str,
    script_rel: str,
    source_dir: Path,
    runtime_config: Any,
    sensitive_dropped: list[Path],
) -> None:
    """Print what ``bindu deploy`` *would* do without doing it."""
    from bindu.runtime.source_packager import (
        IgnoreSpec,
        _walk_included,
        build_tarball,
    )

    spec = IgnoreSpec.load(source_dir)
    included = _walk_included(source_dir, spec)
    blob_size = len(build_tarball(source_dir))

    print("DRY RUN — nothing will be deployed.\n")
    print(f"  agent name:    {agent_name}")
    print(f"  source root:   {source_dir}")
    print(f"  entry script:  {script_rel}")
    print(f"  provider:      {runtime_config.provider}")
    if runtime_config.image:
        print(f"  image (A1):    {runtime_config.image}")
    else:
        vcpu = runtime_config.vcpu if runtime_config.vcpu is not None else "org default"
        memory = runtime_config.memory or "org default"
        print(f"  vcpu / memory: {vcpu} / {memory}")
        if runtime_config.disk:
            print(f"  disk:          {runtime_config.disk}")
        print(f"  auto_suspend:  {runtime_config.auto_suspend}s")
        print(f"  on_exit:       {runtime_config.on_exit}")
        if runtime_config.bindu_version:
            print(f"  bindu_version: {runtime_config.bindu_version}")
    if runtime_config.env:
        print(f"  env keys:      {sorted(runtime_config.env)}  (values hidden)")
    print(
        f"  tarball:       {len(included)} files, {blob_size / 1024:.1f} KB compressed"
    )
    if sensitive_dropped:
        print()
        print("  WARNING: the following files were silently DROPPED from the tarball")
        print("  because they look like secrets. Use --env KEY=VALUE for runtime")
        print("  injection instead:")
        for p in sensitive_dropped:
            print(f"    - {p.relative_to(source_dir)}")


def _handle_deploy(args: argparse.Namespace) -> None:
    """Handle ``bindu deploy <script>``: capture metadata → deploy → supervise."""
    from bindu.runtime import RuntimeConfig, get_provider
    from bindu.runtime.source_packager import find_project_root, find_sensitive_files

    script_path = os.path.abspath(args.script)
    if not os.path.isfile(script_path):
        sys.exit(f"Error: script not found: {script_path}")

    captured = _capture_agent_metadata(script_path)
    agent_name = args.name or captured["agent_name"]
    caller_dir = Path(captured["caller_dir"])
    source_dir = find_project_root(caller_dir)

    try:
        script_rel = str(Path(script_path).resolve().relative_to(source_dir)).replace(
            "\\", "/"
        )
    except ValueError:
        sys.exit(
            f"Error: script {script_path} is not under detected source root "
            f"{source_dir}. Run from the project root or pass an absolute path "
            "to a script inside the project."
        )

    runtime_config = RuntimeConfig.from_dict(_build_runtime_dict(args))
    if runtime_config.provider == "in-process":
        sys.exit("Error: 'bindu deploy' requires a non-default --runtime")

    sensitive = find_sensitive_files(source_dir)

    if args.dry_run:
        _print_dry_run(
            agent_name=agent_name,
            script_rel=script_rel,
            source_dir=source_dir,
            runtime_config=runtime_config,
            sensitive_dropped=sensitive,
        )
        return

    if sensitive:
        print(
            "warning: dropped {} sensitive file(s) from the deploy tarball "
            "(use --dry-run to list, --env KEY=VALUE to inject secrets)".format(
                len(sensitive)
            ),
            file=sys.stderr,
            flush=True,
        )

    provider = get_provider(runtime_config.provider)

    async def _run() -> None:
        handle = await provider.deploy(
            agent_name=agent_name,
            source_dir=source_dir,
            config=runtime_config,
            env=None,
            script=script_rel,
        )
        print(f"\n✓ {agent_name} serving at {handle.url}\n", flush=True)
        await _supervise(provider, handle, runtime_config)

    asyncio.run(_run())


def main() -> None:
    """Run the Bindu CLI."""
    parser = argparse.ArgumentParser(prog="bindu", description="Bindu Framework CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    serve_parser = subparsers.add_parser(
        "serve", help="Start the Bindu core or execute a user agent script"
    )
    serve_parser.add_argument(
        "--grpc",
        action="store_true",
        help="Enable gRPC server for SDK registration",
    )
    serve_parser.add_argument(
        "--grpc-port",
        type=int,
        default=3774,
        help="gRPC server port (default: 3774)",
    )
    serve_parser.add_argument(
        "--script",
        type=str,
        default=None,
        help="Path to a user agent script that calls bindufy()",
    )

    logs_parser = subparsers.add_parser("logs", help="Stream agent logs from its VM")
    logs_parser.add_argument("agent", type=str, help="Agent name")
    logs_parser.add_argument(
        "--no-follow",
        action="store_true",
        help="Print available log content and exit (do not follow)",
    )

    shell_parser = subparsers.add_parser(
        "shell", help="Open an interactive shell on the agent's VM"
    )
    shell_parser.add_argument("agent", type=str, help="Agent name")

    deploy_parser = subparsers.add_parser(
        "deploy",
        help="Package a bindu agent script and deploy it via a RuntimeProvider",
    )
    deploy_parser.add_argument(
        "script", type=str, help="Path to the user agent script that calls bindufy()"
    )
    deploy_parser.add_argument(
        "--runtime",
        type=str,
        default="boxd",
        help="Runtime provider (default: boxd)",
    )
    deploy_parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Override the agent name from the script's config",
    )
    deploy_parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="A1 mode: deploy from this image instead of shipping source",
    )
    deploy_parser.add_argument("--vcpu", type=int, default=None)
    deploy_parser.add_argument("--memory", type=str, default=None)
    deploy_parser.add_argument("--disk", type=str, default=None)
    deploy_parser.add_argument(
        "--auto-suspend",
        type=int,
        default=None,
        dest="auto_suspend",
        help="Seconds idle before the VM auto-suspends",
    )
    deploy_parser.add_argument(
        "--on-exit",
        type=str,
        choices=("suspend", "destroy", "detach"),
        default=None,
        dest="on_exit",
    )
    deploy_parser.add_argument(
        "--bindu-version",
        type=str,
        default=None,
        dest="bindu_version",
        help=(
            "Pin bindu version installed in the VM. Use 'local' to ship the "
            "host's bindu source instead of pulling from PyPI."
        ),
    )
    deploy_parser.add_argument(
        "--env",
        action="append",
        default=None,
        metavar="KEY=VALUE",
        help="Extra env var for the agent inside the VM (repeatable)",
    )
    deploy_parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=False,
        help="Print what would be deployed (target VM, files, env keys) and exit.",
    )

    args = parser.parse_args()

    if args.command == "serve":
        _handle_serve(args)
    elif args.command == "logs":
        asyncio.run(_handle_logs(args.agent, follow=not args.no_follow))
    elif args.command == "shell":
        asyncio.run(_handle_shell(args.agent))
    elif args.command == "deploy":
        _handle_deploy(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
