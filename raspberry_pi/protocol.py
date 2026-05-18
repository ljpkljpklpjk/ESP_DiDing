def build_command(command_id: int, cmd: str, **kwargs):
    payload = {"cmd": cmd, "id": command_id}
    payload.update(kwargs)
    return payload


def fmt_value(value, decimals):
    if value is None:
        return "--"
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)
