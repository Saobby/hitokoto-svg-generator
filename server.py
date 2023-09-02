import json
from flask import *
import requests

app = Flask(__name__)
app.secret_key = "********"


def gen_returns(success=True, message="OK", data=None, **kwargs):
    ret = {"success": success, "message": message, "data": data}
    for k, v in kwargs.items():
        ret[k] = v
    return json.dumps(ret)


def get_client_ip():
    ip_addr = request.headers.get("ry-proxy-real-ip")
    if ip_addr is not None:
        return ip_addr
    ip_addr = request.headers.get("CF-Connecting-IP")
    if ip_addr is not None:
        return ip_addr
    ip_addr = request.headers.get("x-forwarded-for")
    if ip_addr is not None:
        return ip_addr
    ip_addr = request.remote_addr
    return ip_addr


def get_char_width(char):
    if char in "1234567890-=_+,.<>/?[]\\{}|;':\"abcdefghijklmnopqrstuvwxyzIJ`~!@#$%^&*()":
        return 0.5
    else:
        return 1


def rsc(e):
    return e.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


@app.route("/api/hitokoto", methods=["get"])
def api_hitokoto():
    font_size = request.args.get("font_size")
    font_color = request.args.get("font_color")
    show_author = request.args.get("show_author")
    width = request.args.get("width")
    sentence_type = request.args.get("sentence_type")
    max_length = request.args.get("max_length")
    min_length = request.args.get("min_length")
    if None in [font_size, font_color]:
        return abort(400)
    try:
        font_size = int(font_size)
        if width is not None and width != "__auto__":
            hitokoto_width = int(width)
            author_width = int(width)
            width = int(width)
            if width < font_size:
                return abort(400)
        else:
            hitokoto_width = "__auto__"
            author_width = "__auto__"
            width = "__auto__"
        if max_length is not None:
            max_length = int(max_length)
        else:
            max_length = 30
        if min_length is not None:
            min_length = int(min_length)
        else:
            min_length = 0
    except ValueError:
        return abort(400)
    if font_size <= 0:
        return abort(400)
    if len(font_color) not in [3, 6]:
        return abort(400)
    for c in font_color:
        if c.upper() not in "1234567890ABCDEF":
            return abort(400)
    if show_author is None:
        show_author = "true"
    if show_author not in ["true", "false"]:
        return abort(400)
    show_author = {"true": True, "false": False}[show_author]
    if sentence_type is None:
        sentence_type = "__all__"
    if sentence_type == "__all__":
        sentence_types = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"]
    else:
        try:
            sentence_types = json.loads(sentence_type)
        except:
            return abort(400)
    if not isinstance(sentence_types, list):
        return abort(400)
    for i in sentence_types:
        if not isinstance(i, str) or i not in "abcdefghijkl":
            return abort(400)
    if min_length < 0:
        return abort(400)
    if max_length < min_length:
        return abort(400)
    arg_c = "&".join(["c="+t for t in sentence_types])
    api_url = "https://international.v1.hitokoto.cn/?{}&encode=json&charset=utf-8&min_length={}&max_length={}".format(
        arg_c, min_length, max_length)
    api_headers = {"Accept": "application/json", "User-Agent": "s@saobby.com"}
    rep = requests.get(api_url, headers=api_headers)
    rep = json.loads(rep.text)
    sentence = rep["hitokoto"]
    if rep["from_who"] is None:
        author = rep["from"]
    else:
        author = rep["from"] + "/" + rep["from_who"]
    author = "——" + author
    # sentence = "欲买桂花同载酒，荒泷天下第一斗。"
    # author = "——原神/钟离&荒泷一斗"  # &号未转义导致渲染错误
    sentence = rsc(sentence)
    author = rsc(author)
    svg_inner = ""
    current_width = 0
    line = ""
    line_number = 1
    index = 0
    hitokoto_height = 0
    for char in sentence:
        char_width = font_size * get_char_width(char)
        if hitokoto_width != "__auto__" and current_width + char_width > hitokoto_width:
            svg_inner += '<text x="0" y="{y}" fill="#{color}" font-size="{size}">{text}</text>'.format(
                y=line_number*font_size*1.35, color=font_color, size=font_size, text=line)
            current_width = 0
            line = ""
            line_number += 1
        line += char
        current_width += char_width
        index += 1
        if index == len(sentence):
            svg_inner += '<text x="0" y="{y}" fill="#{color}" font-size="{size}">{text}</text>'.format(
                y=line_number*font_size*1.35, color=font_color, size=font_size, text=line)
            if hitokoto_width == "__auto__":
                hitokoto_width = current_width
            hitokoto_height = line_number*font_size*1.35
    if show_author:
        current_width = 0
        line = ""
        line_number = 1
        index = 0
        for char in author:
            char_width = font_size * get_char_width(char)
            if author_width != "__auto__" and current_width + char_width > author_width:
                svg_inner += '<text x="0" y="{y}" fill="#{color}" font-size="{size}">{text}</text>'.format(
                    y=hitokoto_height+line_number*font_size*1.35, color=font_color, size=font_size, text=line)
                current_width = 0
                line = ""
                line_number += 1
            current_width += char_width
            line += char
            index += 1
            if index == len(author):
                line_width = 0
                for c in line:
                    line_width += get_char_width(c)*font_size
                if author_width == "__auto__":
                    author_width = max([line_width, hitokoto_width])
                svg_inner += '<text x="{x}" y="{y}" fill="#{color}" font-size="{size}">{text}</text>'.format(
                    x=author_width-line_width, y=hitokoto_height+line_number*font_size*1.35, color=font_color,
                    size=font_size, text=line)
                hitokoto_height += line_number*font_size*1.35
    if author_width == "__auto__":
        author_width = 0
    if width == "__auto__":
        width = max([author_width, hitokoto_width])
    svg_inner = '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" height="{height}" width="{width}">'.format(
        height=hitokoto_height+0.2*font_size, width=width+0.0962*font_size) + svg_inner + "</svg>"
    return svg_inner


@app.errorhandler(400)
def error_400(err):
    if request.path == "/api/hitokoto":
        return send_file("400.svg"), 400
    return gen_returns(False, "参数错误"), 400


@app.errorhandler(401)
def error_401(err):
    return gen_returns(False, "身份验证失败")


@app.errorhandler(403)
def error_403(err):
    return gen_returns(False, "权限不足"), 403


@app.errorhandler(404)
def error_404(err):
    return gen_returns(False, "你访问的页面不存在"), 404


@app.errorhandler(500)
def error_500(err):
    if request.path == "/api/hitokoto":
        return send_file("500.svg"), 500
    return gen_returns(False, "服务器内部错误!请发邮件到bugs@saobby.com以报告问题"), 500


@app.after_request
def add_header(r):
    if "/api/" in request.path:
        r.headers["Content-Type"] = "application/json; charset=utf-8"
        r.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
    if request.path == "/api/hitokoto":
        r.headers["Content-Type"] = "image/svg+xml; charset=utf-8"
    if request.headers.get("origin") is not None:
        r.headers["Access-Control-Allow-Origin"] = request.headers.get("origin")
    else:
        r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "*"
    r.headers["Access-Control-Allow-Credentials"] = "true"
    r.headers["Access-Control-Allow-Methods"] = "*"
    r.headers["Access-Control-Max-Age"] = "600"
    r.headers["Access-Control-Expose-Headers"] = "*"
    return r


if __name__ == "__main__":
    app.run(port=9998)
