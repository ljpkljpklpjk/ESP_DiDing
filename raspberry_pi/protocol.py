def build_command(command_id: int, cmd: str, **kwargs):
    payload = {"cmd": cmd, "id": command_id}
    payload.update(kwargs)
    return payload


def first_value(data, *keys, default=None):
    for key in keys:
        if isinstance(data, dict) and key in data and data[key] is not None:
            return data[key]
    return default


def fmt_value(value, decimals):
    if value is None:
        return "--"
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)
