from tornado import websocket, web, ioloop
from tornado.options import options, define, parse_command_line
import json
import seolint
from goose import Goose
import os

parse_command_line()

class IndexHandler(web.RequestHandler):
    def get(self):
        server = os.environ.get("DOMAIN","localhost:8888")
        self.render("index.html", server=server)


class SocketHandler(websocket.WebSocketHandler):
    def on_message(self, message):
        self.write_message(json.dumps({'status':10,'msg': 'abriendo url'}))

        if not 'http' in message:
            self.write_message(json.dumps({'error':True, 'msg':'Url Invalida falta el http(s)://'}))
            self.close()
            return


        try:
            tree = seolint.url_open(message)
        except IOError:
            self.write_message(json.dumps({'error':True, 'msg':'Url Invalida'}))
            self.close()
            return
        self.write_message(json.dumps({'status':30,'msg': 'getting tags'}))
        tags = seolint.tags(tree)
        self.write_message(json.dumps({'status':40,'msg': 'obteniendo frecuencia...'}))
        frecuency = seolint.frequency(tree)
        self.write_message(json.dumps({'status':50,'msg': 'obteniendo digrams and trigrams...'}))
        digrams = seolint.frequency(tree, ngram_size=2)
        trigrams = seolint.frequency(tree, ngram_size=3)
        self.write_message(json.dumps({'status':70,'msg': 'check links...'}))
        check_links = seolint.check_links(message, tree, timeout=10)
        self.write_message(json.dumps({'status':80,'msg': 'getting Text and metadata'}))
        g = Goose()
        article = g.extract(url =message)
        self.write_message(json.dumps({'status':100,'msg': 'DONE!'}))
        img = article.top_image.src if article.top_image else None
        result = {
                'tags':tags, 'frequency': frecuency,
                'digrams': digrams,'trigrams': trigrams,
                'check_links': check_links,
                'article': {
                    'title': article.title,
                    'desc': article.meta_description,
                    'text': article.cleaned_text,
                    'top_image': img,
                }
                }
        self.write_message(json.dumps(result))
        self.close()

app = web.Application([
    (r'/', IndexHandler),
    (r'/ws', SocketHandler),
#    (r'/api', ApiHandler),
#    (r'/(favicon.ico)', web.StaticFileHandler, {'path': '../'}),
#    (r'/(rest_api_example.png)', web.StaticFileHandler, {'path': './'}),
],
  autoreload=True, debug=True, compiled_template_cache=False, serve_traceback=True)


if __name__ == '__main__':
    app.listen(8888)
    ioloop.IOLoop.instance().start()
