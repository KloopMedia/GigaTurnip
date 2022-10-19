from rest_framework.renderers import JSONRenderer


class EmberJSONRenderer(JSONRenderer):

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return super(EmberJSONRenderer, self).render(data, accepted_media_type, renderer_context)