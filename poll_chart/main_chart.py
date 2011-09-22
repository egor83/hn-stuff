from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
import os
import logging
from poll_chart import make_chart

class ChartMain(webapp.RequestHandler):
    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'templates/poll_chart.html')
        self.response.out.write(template.render(path, {}))

class MakeChart(webapp.RequestHandler):
    def get(self):
        thread_id = self.request.get('thread_id')
        chart_type = self.request.get('chart_type')
        if self.request.get('show_percents') == 'on':
            show_percents = True
        else:
            show_percents = False

        try:
            pic_url = make_chart.create_chart(thread_id, chart_type,
                                                             show_percents)
        except make_chart.NoPollError:
            self.redirect('/poll_chart/error/?type=NoPollError&thread_id=%s'
            % thread_id)
            return
        except make_chart.NoPollOrNotHNPageError:
            self.redirect('/poll_chart/error/?type=NoPollOrNotHNPageError&\
thread_id=%s' % thread_id)
            return
        except make_chart.NoDataError:
            self.redirect('/poll_chart/error/?type=NoDataError&thread_id=%s'
            % thread_id)
            return

        if pic_url != '':
            path = os.path.join(os.path.dirname(__file__),
                                'templates/result.html')
            template_values = {
                'thread_id': thread_id,
                'pic_url': pic_url
            }
            self.response.out.write(template.render(path, template_values))
        else:
            # url empty, error has occurred
            self.redirect('/poll_chart/error/')
            
        logging.info('pic url: %s' % pic_url)

    def handle_exception(self, exception, mode):
        # from http://bit.ly/gZLnrk

        webapp.RequestHandler.handle_exception(self, exception, mode)
        logging.error("Exception has occured while making a chart: %s",
                      str(exception))
        self.redirect('/poll_chart/error/')
        return

class ErrorPage(webapp.RequestHandler):
    def get(self):
        thread_id = self.request.get('thread_id')
        error_type = self.request.get('type')
        error_template = 'templates/error.html'

        if error_type == 'NoPollError':
            error_template = 'templates/NoPollError.html'
        elif error_type == 'NoPollOrNotHNPageError':
            error_template = 'templates/NoPollOrNotHNPageError.html'
        elif error_type == 'NoDataError':
            error_template = 'templates/NoDataError.html'

        path = os.path.join(os.path.dirname(__file__), error_template)
        self.response.out.write(template.render(path, {'thread_id':thread_id}))

class IntroPage(webapp.RequestHandler):
    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'templates/intro.html')
        self.response.out.write(template.render(path, {}))

def main():
    logging.getLogger().setLevel(logging.DEBUG)
    application = webapp.WSGIApplication([('/poll_chart', ChartMain),
                                            ('/poll_chart/', ChartMain),
                                            ('/poll_chart/build', MakeChart),
                                            ('/poll_chart/build/', MakeChart),
                                            ('/poll_chart/error', ErrorPage),
                                            ('/poll_chart/error/', ErrorPage),
                                            ('/poll_chart/intro', IntroPage),
                                            ('/poll_chart/intro/', IntroPage)
                                            ], debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
