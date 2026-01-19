#!/usr/bin/python3
# coding: utf-8

# ========== Init ==========

# region init

# show welcome text
print(
    f"""
Welcome to Sleepy Project 2025!
Give us a Star 🌟 please: https://github.com/sleepy-project/sleepy
Bug Report: https://sleepy.wss.moe/bug
Feature Request: https://sleepy.wss.moe/feature
Security Report: https://sleepy.wss.moe/security
"""[
        1:
    ],
    flush=True,
)

# import modules
try:
    # built-in
    import logging
    from datetime import datetime, timedelta, timezone
    import time
    from urllib.parse import urlparse, parse_qs, urlunparse
    import json
    from traceback import format_exc
    from mimetypes import guess_type

    # 3rd-party
    import flask
    from flask_cors import cross_origin
    from markupsafe import escape
    from werkzeug.exceptions import NotFound, HTTPException
    from toml import load as load_toml
    from flasgger import Swagger

    # local modules
    from config import Config as config_init
    import utils as u
    from data import Data as data_init
    import plugin as pl
except:
    print(
        f"""
Import module Failed!
 * Please make sure you installed all dependencies in requirements.txt
 * If you don't know how, see doc/deploy.md
 * If you believe that's our fault, report to us: https://sleepy.wss.moe/bug
 * And provide the logs (below) to us:
"""[
            1:-1
        ],
        flush=True,
    )
    raise

try:
    # get version info
    with open(u.get_path("pyproject.toml"), "r", encoding="utf-8") as f:
        file: dict = load_toml(f).get("tool", {}).get("sleepy-plugin", {})
        version_str: str = file.get("version-str", "unknown")
        version: tuple[int, int, int] = tuple(file.get("version", (0, 0, 0)))
        f.close()

    # init flask app
    app = flask.Flask(
        import_name=__name__,
        template_folder="theme/default/templates",
        static_folder=None,
    )
    app.json.ensure_ascii = False  # type: ignore - disable json ensure_ascii

    # init logger
    l = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # clear default handler
    # set stream handler
    shandler = logging.StreamHandler()
    shandler.setFormatter(u.CustomFormatter(colorful=False))
    root_logger.addHandler(shandler)

    # init config
    c = config_init().config

    # continue init logger
    root_logger.level = logging.DEBUG if c.main.debug else logging.INFO  # set log level
    # reset stream handler
    root_logger.handlers.clear()
    shandler = logging.StreamHandler()
    shandler.setFormatter(
        u.CustomFormatter(colorful=c.main.colorful_log, timezone=c.main.timezone)
    )
    root_logger.addHandler(shandler)
    # set file handler
    if c.main.log_file:
        log_file_path = u.get_path(c.main.log_file)
        l.info(f"Saving logs to {log_file_path}")
        fhandler = logging.FileHandler(log_file_path, encoding="utf-8", errors="ignore")
        fhandler.setFormatter(
            u.CustomFormatter(colorful=False, timezone=c.main.timezone)
        )
        root_logger.addHandler(fhandler)

    l.info(f'{"="*15} Application Startup {"="*15}')
    l.info(f'Sleepy Server version {version_str} ({".".join(str(i) for i in version)})')

    # debug: disable static cache
    if c.main.debug:
        app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    else:
        app.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(seconds=c.main.cache_age)

    # disable flask access log
    logging.getLogger("werkzeug").disabled = True
    from flask import cli

    cli.show_server_banner = lambda *_: None

    # init data
    d = data_init(config=c, app=app)

    # init metrics if enabled
    if c.metrics.enabled:
        l.info("[metrics] metrics enabled, open /api/metrics to see the count.")

    # init plugin
    p = pl.PluginInit(version=version, config=c, data=d, app=app)
    p.load_plugins()

except KeyboardInterrupt:
    l.info("Interrupt init, quitting")
    exit(0)
except u.SleepyException as e:
    l.critical(e)
    exit(2)
except:
    l.critical(f"Unexpected Error!\n{format_exc()}")
    exit(3)

p.trigger_event(pl.AppInitializedEvent())

# endregion init

# ========== Theme ==========

# region theme


def render_template(
    filename: str, _dirname: str = "templates", _theme: str | None = None, **context
) -> str:
    """
    渲染模板 (使用指定主题)

    :param filename: 文件名
    :param _dirname: `theme/[主题名]/<dirname>/<filename>`
    :param _theme: 主题 (未指定则从 `flask.g.theme` 读取)
    :param **context: 将传递给 `flask.render_template_string` 的模板上下文
    :return: 渲染后的 HTML 字符串,如果模板不存在则返回空字符串
    """
    _theme = _theme or flask.g.theme
    content = d.get_cached_text("theme", f"{_theme}/{_dirname}/{filename}")
    if content:
        l.debug(f"[theme] return template {_dirname}/{filename} from theme {_theme}")
        return flask.render_template_string(content, **context)

    content = d.get_cached_text("theme", f"default/{_dirname}/{filename}")
    if content:
        l.debug(f"[theme] return template {_dirname}/{filename} from default theme")
        return flask.render_template_string(content, **context)

    l.warning(f"[theme] template {_dirname}/{filename} not found")
    return ""


@app.route("/static/<path:filename>", endpoint="static")
def static_proxy(filename: str):
    """
    静态文件的主题处理 (重定向到 /static-themed/主题名/文件名)
    """
    # 重定向
    return u.no_cache_response(
        flask.redirect(f"/static-themed/{flask.g.theme}/{filename}", 302)
    )


@app.route("/static-themed/<theme>/<path:filename>")
def static_themed(theme: str, filename: str):
    """
    经过主题分隔的静态文件 (便于 cdn / 浏览器 进行缓存)
    """
    try:
        # 1. 返回主题
        resp = flask.send_from_directory("theme", f"{theme}/static/{filename}")
        l.debug(f"[theme] return static file {filename} from theme {theme}")
        return resp
    except NotFound:
        # 2. 主题不存在 (而且不是默认) -> fallback 到默认
        if theme != "default":
            l.debug(
                f"[theme] static file {filename} not found in theme {theme}, fallback to default"
            )
            return u.no_cache_response(
                flask.redirect(f"/static-themed/default/{filename}", 302)
            )

        # 3. 默认主题也没有 -> 404
        else:
            l.warning(f"[theme] static file {filename} not found")
            return u.no_cache_response(
                f"Static file {filename} in theme {theme} not found!", 404
            )


# endregion theme

# ========== Error Handler ==========

# region errorhandler


@app.errorhandler(u.APIUnsuccessful)
def api_unsuccessful_handler(e: u.APIUnsuccessful):
    """
    处理 `APIUnsuccessful` 错误
    """
    l.error(f"API Calling Error: {e}")
    evt = p.trigger_event(pl.APIUnsuccessfulEvent(e))
    if evt.interception:
        return evt.interception
    return {
        "success": False,
        "code": evt.error.code,
        "details": evt.error.details,
        "message": evt.error.message,
    }, evt.error.code


@app.errorhandler(Exception)
def error_handler(e: Exception):
    """
    处理未捕获运行时错误
    """
    if isinstance(e, HTTPException):
        l.warning(f"HTTP Error: {e}")
        evt = p.trigger_event(pl.HTTPErrorEvent(e))
        if evt.interception:
            return evt.interception
        return evt.error
    else:
        l.error(f"Unhandled Error: {e}\n{format_exc()}")
        evt = p.trigger_event(pl.UnhandledErrorEvent(e))
        if evt.interception:
            return evt.interception
        return f"Unhandled Error: {evt.error}"


# endregion errorhandler

# ========== Request Inject ==========

# region inject


@app.before_request
def before_request():
    """
    before_request:
    - 性能计数器
    - 检测主题参数, 设置 cookie & 去除参数
    - 设置会话变量 (theme, secret)
    """
    flask.g.perf = u.perf_counter()
    fip = flask.request.headers.get("X-Real-IP") or flask.request.headers.get(
        "X-Forwarded-For"
    )
    flask.g.ipstr = (flask.request.remote_addr or "") + (f" / {fip}" if fip else "")

    # --- get theme arg
    if flask.request.args.get("theme"):
        # 提取 theme 并删除
        theme = flask.request.args.get("theme", "default")
        parsed = urlparse(flask.request.full_path)
        params = parse_qs(parsed.query)
        l.debug(f"parsed url: {parsed}")
        if "theme" in params:
            del params["theme"]

        # 构造新查询字符串
        new_params = []
        for key, value in params.items():
            if isinstance(value, list):
                new_params.extend([f"{key}={v}" for v in value])
            else:
                new_params.append(f"{key}={value}")
        new_params_str = "&".join(new_params)

        # 构造新 url
        new_parsed = parsed._replace(query=new_params_str)
        new_url = urlunparse(new_parsed)
        l.debug(f"redirect to new url: {new_url} with theme {theme}")

        # 重定向
        resp = u.no_cache_response(flask.redirect(new_url, 302))
        resp.set_cookie("sleepy-theme", theme, samesite="Lax")
        return resp

    # --- set context vars
    elif flask.request.cookies.get("sleepy-theme"):
        # got sleepy-theme
        flask.g.theme = flask.request.cookies.get("sleepy-theme")
    else:
        # use default theme
        flask.g.theme = c.page.theme
    flask.g.secret = c.main.secret

    evt = p.trigger_event(pl.BeforeRequestHook())
    if evt and evt.interception:
        return evt.interception


@app.after_request
def after_request(resp: flask.Response):
    """
    after_request:
    - 记录 metrics 信息
    - 显示访问日志
    """
    # --- metrics
    path = flask.request.path
    if c.metrics.enabled:
        d.record_metrics(path)
    # --- access log
    l.info(
        f"[Request] {flask.g.ipstr} | {path} -> {resp.status_code} ({flask.g.perf()}ms)"
    )
    evt = p.trigger_event(pl.AfterRequestHook(resp))
    if evt.interception:
        evt.response = flask.Response(evt.interception[0], evt.interception[1])
    evt.response.headers.add(
        "X-Powered-By", "Sleepy-Project (https://github.com/sleepy-project)"
    )
    evt.response.headers.add(
        "Sleepy-Version", f'{version_str} ({".".join(str(i) for i in version)})'
    )
    return evt.response


# endregion inject

# ========== Routes ==========

# 导入路由模块
from routes import register_routes


# ========== End ==========

# region run


p.trigger_event(pl.AppStartedEvent())

if __name__ == "__main__":
    swagger = Swagger(app)
    register_routes(app, l, c, d, p, version, version_str)

    l.info(f"Hi {c.page.name}!")
    listening = (
        f'{f"[{c.main.host}]" if ":" in c.main.host else c.main.host}:{c.main.port}'
    )
    if c.main.https:
        ssl_context = (c.main.ssl_cert, c.main.ssl_key)
        l.info(f"Using SSL: {c.main.ssl_cert} / {c.main.ssl_key}")
        l.info(
            f'Listening service on: https://{listening}{" (debug enabled)" if c.main.debug else ""}'
        )
    else:
        ssl_context = None
        l.info(
            f'Listening service on: http://{listening}{" (debug enabled)" if c.main.debug else ""}'
        )
    try:
        app.run(  # 启↗动↘
            host=c.main.host,
            port=c.main.port,  # type: ignore
            debug=c.main.debug,
            use_reloader=False,
            threaded=True,
            ssl_context=ssl_context,
        )
    except Exception as e:
        l.critical(f"Critical error when running server: {e}\n{format_exc()}")
        p.trigger_event(pl.AppStoppedEvent(1))
        exit(1)
    else:
        print()
        p.trigger_event(pl.AppStoppedEvent(0))
        l.info("Bye.")
        exit(0)

# endregion run
