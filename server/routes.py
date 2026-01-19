#!/usr/bin/python3
# coding: utf-8

# ========== Routes ==========

# region routes

# ----- Special -----

# region routes-special


def register_routes(app, l, c, d, p, version, version_str):
    from flask import request, g, jsonify, abort, redirect
    from flask_cors import cross_origin
    from markupsafe import escape
    from werkzeug.exceptions import NotFound, HTTPException
    import flask
    from datetime import datetime, timezone
    import time
    import json
    from urllib.parse import urlparse, parse_qs, urlunparse
    import utils as u
    from data import Data
    import plugin as pl

    @app.route("/")
    def index():
        """
        根目录返回 html
        - Method: **GET**
        """
        # 获取更多信息 (more_text)
        more_text: str = c.page.more_text
        if c.metrics.enabled:
            daily, weekly, monthly, yearly, total = d.metric_data_index
            more_text = more_text.format(
                visit_daily=daily,
                visit_weekly=weekly,
                visit_monthly=monthly,
                visit_yearly=yearly,
                visit_total=total,
            )
        # 加载系统卡片
        main_card: str = render_template(  # type: ignore
            "main.index.html",
            _dirname="cards",
            username=c.page.name,
            status=d.status_dict[1],
            last_updated=datetime.fromtimestamp(d.last_updated, timezone.utc).strftime(
                f"%Y-%m-%d %H:%M:%S"
            )
            + " (UTC+8)",
        )
        more_info_card: str = render_template(  # type: ignore
            "more_info.index.html",
            _dirname="cards",
            more_text=more_text,
            username=c.page.name,
            learn_more_link=c.page.learn_more_link,
            learn_more_text=c.page.learn_more_text,
            available_themes=u.themes_available(),
        )

        # 加载插件卡片
        cards = {"main": main_card, "more-info": more_info_card}
        for name, values in p.index_cards.items():
            value = ""
            for v in values:
                if hasattr(v, "__call__"):
                    value += f"{v()}<br/>\n"  # type: ignore - pylance 不太行啊 (?"
                else:
                    value += f"{v}<br/>\n"
            cards[name] = value

        # 处理主页注入
        injects: list[str] = []
        for i in p.index_injects:
            if hasattr(i, "__call__"):
                injects.append(str(i()))  # type: ignore
            else:
                injects.append(str(i))

        evt = p.trigger_event(
            pl.IndexAccessEvent(
                page_title=c.page.title,
                page_desc=c.page.desc,
                page_favicon=c.page.favicon,
                page_background=c.page.background,
                cards=cards,
                injects=injects,
            )
        )

        if evt.interception:
            return evt.interception

        # 返回 html
        return render_template(
            "index.html",
            page_title=evt.page_title,
            page_desc=evt.page_desc,
            page_favicon=evt.page_favicon,
            page_background=evt.page_background,
            cards=evt.cards,
            inject="\n".join(evt.injects),
        ) or flask.abort(404)

    @app.route("/favicon.ico")
    def favicon():
        """
        重定向 /favicon.ico 到用户自定义的 favicon
        """
        evt = p.trigger_event(pl.FaviconAccessEvent(c.page.favicon))
        if evt.interception:
            return evt.interception
        return (
            flask.redirect(evt.favicon_url, 302)
            if evt.favicon_url != "/favicon.ico"
            else serve_public("favicon.ico")
        )

    @app.route("/" + "git" + "hub")
    def git_hub():
        """
        这里谁来了都改不了!
        """
        # ~~我要改~~
        # ~~-- NT~~
        # **不准改, 敢改我就撤了你的 member** -- wyf9
        # noooooooooooooooo -- NT
        return flask.redirect(
            "ht"
            + "tps:"
            + "//git"
            + "hub.com/"
            + "slee"
            + "py-"
            + "project/sle"
            + "epy",
            301,
        )

    @app.route("/none")
    def none():
        """
        返回 204 No Content, 可用于 Uptime Kuma 等工具监控服务器状态使用
        """
        return "", 204

    @app.route("/api/meta")
    @cross_origin(c.main.cors_origins)
    def metadata():
        """
        获取站点元数据
        """
        meta = {
            "success": True,
            "version": version,
            "version_str": version_str,
            "timezone": c.main.timezone,
            "page": {
                "name": c.page.name,
                "title": c.page.title,
                "desc": c.page.desc,
                "favicon": c.page.favicon,
                "background": c.page.background,
                "theme": c.page.theme,
            },
            "status": {
                "device_slice": c.status.device_slice,
                "refresh_interval": c.status.refresh_interval,
                "not_using": c.status.not_using,
                "sorted": c.status.sorted,
                "using_first": c.status.using_first,
            },
            "metrics": c.metrics.enabled,
        }
        evt = p.trigger_event(pl.MetadataAccessEvent(meta))
        if evt.interception:
            return evt.interception
        return evt.metadata

    @app.route("/api/metrics")
    @cross_origin(c.main.cors_origins)
    def metrics():
        """
        获取统计信息
        - Method: **GET**
        """
        evt = p.trigger_event(pl.MetricsAccessEvent(d.metrics_resp))
        if evt.interception:
            return evt.interception
        return evt.metrics_response

    # endregion routes-special

    # ----- Status -----

    # region routes-status

    @app.route("/api/status/query")
    @cross_origin(c.main.cors_origins)
    def query_route():
        """
        获取系统当前状态
        返回设备列表、运行状态、最后更新时间等信息。
        ---
        tags:
          - 状态 (Status)
        parameters:
          - name: meta
            in: query
            type: boolean
            required: false
            description: 是否在响应中包含站点元数据
          - name: metrics
            in: query
            type: boolean
            required: false
            description: 是否在响应中包含访问统计信息
        responses:
          200:
            description: 成功返回状态信息
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                time:
                  type: number
                  example: 1700000000.123
                status:
                  type: object
                device:
                  type: array
                last_updated:
                  type: number
                  example: 1700000000
        """
        return query()

    def query():
        """
        获取当前状态
        - 无需鉴权
        - Method: **GET**
        """
        st: int = d.status_id
        try:
            stinfo = c.status.status_list[st].model_dump()
        except (IndexError, AttributeError):
            stinfo = {
                "id": -1,
                "name": "[未知]",
                "desc": f"未知的标识符 {st}，可能是配置问题。",
                "color": "error",
            }

        ret = {
            "success": True,
            "time": datetime.now().timestamp(),
            "status": stinfo,
            "device": d.device_list,
            "last_updated": d.last_updated,
        }

        if flask.request:
            if u.tobool(flask.request.args.get("meta", False)):
                ret["meta"] = metadata()
            if u.tobool(flask.request.args.get("metrics", False)):
                ret["metrics"] = d.metrics_resp

        evt = p.trigger_event(pl.QueryAccessEvent(ret))
        return evt.query_response

    def _event_stream(event_id: int, ipstr: str):
        last_updated = None
        last_heartbeat = time.time()

        l.info(f"[SSE] Event stream connected: {ipstr}")
        while True:
            current_time = time.time()
            # 检查数据是否已更新
            current_updated = d.last_updated

            # 如果数据有更新, 发送更新事件并重置心跳计时器
            if last_updated != current_updated:
                last_updated = current_updated
                # 重置心跳计时器
                last_heartbeat = current_time

                # 获取 /query 返回数据
                update_data = json.dumps(query(), ensure_ascii=False)
                event_id += 1
                yield f"id: {event_id}\nevent: update\ndata: {update_data}\n\n"

            # 只有在没有数据更新的情况下才检查是否需要发送心跳
            elif current_time - last_heartbeat >= 30:
                event_id += 1
                yield f"id: {event_id}\nevent: heartbeat\ndata:\n\n"
                last_heartbeat = current_time

            time.sleep(1)  # 每秒检查一次更新

    @app.route("/api/status/events")
    @cross_origin(c.main.cors_origins)
    def events():
        """
        SSE 事件流，用于推送状态更新
        - Method: **GET**
        """
        try:
            last_event_id = int(flask.request.headers.get("Last-Event-ID", "0"))
        except ValueError:
            raise u.APIUnsuccessful(
                400, "Invaild Last-Event-ID header, it must be int!"
            )

        evt = p.trigger_event(pl.StreamConnectedEvent(last_event_id))
        if evt.interception:
            return evt.interception
        ipstr: str = flask.g.ipstr

        response = flask.Response(
            _event_stream(last_event_id, ipstr),
            mimetype="text/event-stream",
            status=200,
        )
        response.headers["Cache-Control"] = "no-cache"  # 禁用缓存
        response.headers["X-Accel-Buffering"] = "no"  # 禁用 Nginx 缓冲
        response.call_on_close(
            lambda: (
                l.info(f"[SSE] Event stream disconnected: {ipstr}"),
                p.trigger_event(pl.StreamDisconnectedEvent()),
            )
        )
        return response

    @app.route("/api/status/set")
    @cross_origin(c.main.cors_origins)
    @u.require_secret()
    def set_status():
        """
        设置状态
        - http[s]://<your-domain>[:your-port]/set?status=<a-number>
        - Method: **GET**
        """
        status = escape(flask.request.args.get("status"))
        try:
            status = int(status)
        except (TypeError, ValueError):
            raise u.APIUnsuccessful(400, "argument 'status' must be int")

        if status != d.status_id:
            old_status = d.status
            new_status = d.get_status(status)
            evt = p.trigger_event(
                pl.StatusUpdatedEvent(
                    old_exists=old_status[0],
                    old_status=old_status[1],
                    new_exists=new_status[0],
                    new_status=new_status[1],
                )
            )
            if evt.interception:
                return evt.interception
            status = evt.new_status.id
            d.status_id = status

        return {"success": True, "set_to": status}

    @app.route("/api/status/list")
    @cross_origin(c.main.cors_origins)
    def get_status_list():
        """
        获取 `status_list`
        - 无需鉴权
        - Method: **GET**
        """
        evt = p.trigger_event(pl.StatuslistAccessEvent(c.status.status_list))
        if evt.interception:
            return evt.interception
        return {
            "success": True,
            "status_list": [i.model_dump() for i in evt.status_list],
        }

    # endregion routes-status

    # ----- Device -----

    # region routes-device

    @app.route("/api/device/set", methods=["GET", "POST"])
    @cross_origin(c.main.cors_origins)
    @u.require_secret()
    def device_set():
        """
        设置单个设备的信息/打开应用
        - Method: **GET / POST**
        """
        # 分 get / post 从 params / body 获取参数
        if flask.request.method == "GET":
            args = dict(flask.request.args)
            device_id = args.pop("id", None)
            device_show_name = args.pop("show_name", None)
            device_using = u.tobool(args.pop("using", None))
            device_status = args.pop("status", None) or args.pop(
                "app_name", None
            )  # 兼容旧版名称
            args.pop("secret", None)

            evt = p.trigger_event(
                pl.DeviceSetEvent(
                    device_id=device_id,
                    show_name=device_show_name,
                    using=device_using,
                    status=device_status,
                    fields=args,
                )
            )
            if evt.interception:
                return evt.interception

            d.device_set(
                id=evt.device_id,
                show_name=evt.show_name,
                using=evt.using,
                status=evt.status,
                fields=evt.fields,
            )

        elif flask.request.method == "POST":
            try:
                req: dict = flask.request.get_json()

                evt = p.trigger_event(
                    pl.DeviceSetEvent(
                        device_id=req.get("id"),
                        show_name=req.get("show_name"),
                        using=req.get("using"),
                        status=req.get("status") or req.get("app_name"),  # 兼容旧版名称
                        fields=req.get("fields") or {},
                    )
                )
                if evt.interception:
                    return evt.interception

                d.device_set(
                    id=evt.device_id,
                    show_name=evt.show_name,
                    using=evt.using,
                    status=evt.status,
                    fields=evt.fields,
                )
            except Exception as e:
                if isinstance(e, u.APIUnsuccessful):
                    raise e
                else:
                    raise u.APIUnsuccessful(
                        400, f"missing param or wrong param type: {e}"
                    )
        else:
            raise u.APIUnsuccessful(
                405, "/api/device/set only supports GET and POST method!"
            )

        return {"success": True}

    @app.route("/api/device/remove")
    @cross_origin(c.main.cors_origins)
    @u.require_secret()
    def device_remove():
        """
        移除单个设备的状态
        - Method: **GET**
        """
        device_id = flask.request.args.get("id")
        if not device_id:
            raise u.APIUnsuccessful(400, "Missing device id!")

        device = d.device_get(device_id)

        if device:
            evt = p.trigger_event(
                pl.DeviceRemovedEvent(
                    exists=True,
                    device_id=device_id,
                    show_name=device.show_name,
                    using=device.using,
                    status=device.status,
                    fields=device.fields,
                )
            )
        else:
            evt = p.trigger_event(
                pl.DeviceRemovedEvent(
                    exists=False,
                    device_id=device_id,
                    show_name=None,
                    using=None,
                    status=None,
                    fields=None,
                )
            )

        if evt.interception:
            return evt.interception

        d.device_remove(evt.device_id)

        return {"success": True}

    @app.route("/api/device/clear")
    @cross_origin(c.main.cors_origins)
    @u.require_secret()
    def device_clear():
        """
        清除所有设备状态
        - Method: **GET**
        """
        evt = p.trigger_event(pl.DeviceClearedEvent(d._raw_device_list))
        if evt.interception:
            return evt.interception

        d.device_clear()

        return {"success": True}

    @app.route("/api/device/private")
    @u.require_secret()
    @cross_origin(c.main.cors_origins)
    def device_private_mode():
        """
        隐私模式, 即不在返回中显示设备状态 (仍可正常更新)
        - Method: **GET**
        """
        private = u.tobool(flask.request.args.get("private"))
        if private == None:
            raise u.APIUnsuccessful(400, "'private' arg must be boolean")
        elif not private == d.private_mode:
            evt = p.trigger_event(pl.PrivateModeChangedEvent(d.private_mode, private))
            if evt.interception:
                return evt.interception

            d.private_mode = evt.new_status

        return {"success": True}

    # endregion routes-device

    # ----- Panel (Admin) -----

    # region routes-panel

    @app.route("/panel")
    @u.require_secret(redirect_to="/panel/login")
    def admin_panel():
        """
        管理面板
        - Method: **GET**
        """

        # 加载管理面板卡片
        cards = {}
        for name, card in p.panel_cards.items():
            if hasattr(card["content"], "__call__"):
                cards[name] = card.copy()
                cards[name]["content"] = card["content"]()  # type: ignore
            else:
                cards[name] = card

        # 处理管理面板注入
        inject = ""
        for i in p.panel_injects:
            if hasattr(i, "__call__"):
                inject += str(i()) + "\n"  # type: ignore
            else:
                inject += str(i) + "\n"

        return render_template(
            "panel.html",
            c=c,
            current_theme=g.theme,
            available_themes=u.themes_available(),
            cards=cards,
            inject=inject,
        ) or flask.abort(404)

    @app.route("/panel/login")
    def login():
        """
        登录页面
        - Method: **GET**
        """
        # 检查是否已经登录（cookie 中是否有有效的 sleepy-secret）
        cookie_token = flask.request.cookies.get("sleepy-secret")
        if cookie_token == c.main.secret:
            # 如果 cookie 有效，直接重定向到管理面板
            return flask.redirect("/panel")

        return render_template("login.html", c=c, current_theme=g.theme) or flask.abort(
            404
        )

    @app.route("/panel/auth", methods=["POST"])
    @u.require_secret()
    def auth():
        """
        处理登录请求，验证密钥并设置 cookie
        - Method: **POST**
        """
        # 创建响应
        response = flask.make_response(
            {"success": True, "code": "OK", "message": "Login successful"}
        )

        # 设置 cookie，有效期为 30 天
        max_age = 30 * 24 * 60 * 60  # 30 days in seconds
        response.set_cookie(
            "sleepy-secret",
            c.main.secret,
            max_age=max_age,
            httponly=True,
            samesite="Lax",
        )

        l.debug("[Panel] Login successful, cookie set")
        return response

    @app.route("/panel/logout")
    def logout():
        """
        处理退出登录请求，清除 cookie
        - Method: **GET**
        """
        # 创建响应
        response = flask.make_response(flask.redirect("/panel/login"))

        # 清除认证 cookie
        response.delete_cookie("sleepy-secret")

        l.debug("[Panel] Logout successful")
        return response

    @app.route("/panel/verify", methods=["GET", "POST"])
    @cross_origin(c.main.cors_origins)
    @u.require_secret()
    def verify_secret():
        """
        验证密钥是否有效
        - Method: **GET / POST**
        """
        l.debug("[Panel] Secret verified")
        return {"success": True, "code": "OK", "message": "Secret verified"}

    # endregion routes-panel

    # if c.util.steam_enabled:
    #     @app.route('/steam-iframe')
    #     def steam():
    #         return flask.render_template(
    #             'steam-iframe.html',
    #             c=c,
    #             steamids=c.util.steam_ids,
    #             steam_refresh_interval=c.util.steam_refresh_interval
    #         )

    @app.route("/<path:path_name>")
    def serve_public(path_name: str):
        """
        服务 `/data/public` / `/public` 文件夹下文件
        """
        l.debug(f"Serving static file: {path_name}")
        file = d.get_cached_file("data/public", path_name) or d.get_cached_file(
            "public", path_name
        )
        if file:
            from mimetypes import guess_type

            mime = guess_type(path_name)[0] or "text/plain"
            return flask.send_file(file, mimetype=mime)
        else:
            return flask.abort(404)

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
            l.debug(
                f"[theme] return template {_dirname}/{filename} from theme {_theme}"
            )
            return flask.render_template_string(content, **context)

        content = d.get_cached_text("theme", f"default/{_dirname}/{filename}")
        if content:
            l.debug(f"[theme] return template {_dirname}/{filename} from default theme")
            return flask.render_template_string(content, **context)

        l.warning(f"[theme] template {_dirname}/{filename} not found")
        return ""

    # @app.route("/static/<path:filename>", endpoint="static_themed")
    # def static_proxy(filename: str):
    #     """
    #     静态文件的主题处理 (重定向到 /static-themed/主题名/文件名)
    #     """
    #     # 重定向
    #     return u.no_cache_response(
    #         flask.redirect(f"/static-themed/{flask.g.theme}/{filename}", 302)
    #     )

    # @app.route("/static-themed/<theme>/<path:filename>")
    # def static_themed(theme: str, filename: str):
    #     """
    #     经过主题分隔的静态文件 (便于 cdn / 浏览器 进行缓存)
    #     """
    #     try:
    #         # 1. 返回主题
    #         resp = flask.send_from_directory("theme", f"{theme}/static/{filename}")
    #         l.debug(f"[theme] return static file {filename} from theme {theme}")
    #         return resp
    #     except NotFound:
    #         # 2. 主题不存在 (而且不是默认) -> fallback 到默认
    #         if theme != "default":
    #             l.debug(
    #                 f"[theme] static file {filename} not found in theme {theme}, fallback to default"
    #             )
    #             return u.no_cache_response(
    #                 flask.redirect(f"/static-themed/default/{filename}", 302)
    #             )

    #         # 3. 默认主题也没有 -> 404
    #         else:
    #             l.warning(f"[theme] static file {filename} not found")
    #             return u.no_cache_response(
    #                 f"Static file {filename} in theme {theme} not found!", 404
    #             )

    # @app.route("/default/<path:filename>")
    # def static_default_theme(filename: str):
    #     """
    #     兼容在非默认主题中使用:
    #     ```
    #     import { ... } from "../../default/static/utils";
    #     ```
    #     """
    #     if not filename.endswith(".js"):
    #         filename += ".js"
    #     return flask.send_from_directory("theme/default", filename)
