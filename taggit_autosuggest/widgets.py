import json

import copy
from django import VERSION
from django import forms
from django.conf import settings
if VERSION < (2, 0):
    from django.core.urlresolvers import reverse
else:
    from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from taggit_autosuggest.utils import edit_string_for_tags

try:
    # django >= 1.7
    from django.apps import apps
    get_model = apps.get_model
except ImportError:
    # django < 1.7
    from django.db.models import get_model


MAX_SUGGESTIONS = getattr(settings, 'TAGGIT_AUTOSUGGEST_MAX_SUGGESTIONS', 20)


class TagAutoSuggest(forms.TextInput):
    input_type = 'text'
    tagmodel = None

    def __init__(self, tagmodel, *args, **kwargs):
        self.tagmodel = tagmodel
        return super(TagAutoSuggest, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None, *args, **kwargs):
        if not value:
            value = []
        if not isinstance(value, str):
            value = list(get_model(self.tagmodel).objects.filter(language_code=self.language_code, id__in=[t.id for t in value]))
        else:
            dict_obj = json.loads(value)
            value = dict_obj['tags']
        if hasattr(value, "select_related"):
            tags = [o.tag for o in value.select_related("tag")]
            value = edit_string_for_tags(tags)
        elif value is not None and not isinstance(value, str):
            value = edit_string_for_tags(value)

        autosuggest_url = reverse('taggit_autosuggest-list', kwargs={'tagmodel': self.tagmodel})

        result_attrs = copy.copy(attrs) if attrs else {}
        initial_input_type, self.input_type = self.input_type, 'hidden'
        result_html = super(TagAutoSuggest, self).render(
            name,
            value,
            result_attrs,
            renderer=renderer,
            *args,
            **kwargs
        )
        self.input_type = initial_input_type

        widget_attrs = copy.copy(attrs) if attrs else {}
        widget_attrs['id'] += '__tagautosuggest'
        widget_html = super(TagAutoSuggest, self).render(
            name,
            value,
            widget_attrs,
            renderer=renderer,
            *args,
            **kwargs
        )

        js = u"""
            <script type="text/javascript">
            (function ($) {
                var tags_as_string;

                String.prototype.toProperCase = function () {
                    return this.replace(/\w\S*/g, function(txt) {
                        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
                    });
                };

                Array.prototype.toUnique = function() {
                    var dict = {},
                        arrayLength = this.length,
                        elem,
                        i,
                        key,
                        uniqueArray = [];
                    for (i = 0; i < arrayLength; i++) {
                        elem = this[i];
                        dict[elem] = elem;
                    }
                    for (key in dict) {
                        uniqueArray.push(key);
                    }
                    return uniqueArray;
                };
                
                function formatToJSON(lang, values) {
                    var obj = new Object();
                    obj.language_code = lang;
                    obj.tags  = values;
                    return JSON.stringify(obj)
                }
                
                function getCookie(cname) {
                  var name = cname + "=";
                  var ca = document.cookie.split(';');
                  for(var i = 0; i < ca.length; i++) {
                    var c = ca[i];
                    while (c.charAt(0) == ' ') {
                      c = c.substring(1);
                    }
                    if (c.indexOf(name) == 0) {
                      return c.substring(name.length, c.length);
                    }
                  }
                  return "";
                }

                
                $(document).ready(function (){
                    tags_as_string = $('#%(result_id)s').val();
                    var searchParams = new URLSearchParams(window.location.search)
                    var tab_lang = ((searchParams.get('language') !== null) ? searchParams.get('language') : getCookie('django_language'))
                                   
     

                    /* Be sure to instantiate it a single time */
                    if (typeof($("#as-selections-" + "%(widget_id)s").get(0)) === 'undefined') {
                        $("#%(widget_id)s").autoSuggest("%(url)s", {
                            asHtmlID: "%(widget_id)s",
                            startText: "%(start_text)s",
                            emptyText: "%(empty_text)s",
                            limitText: "%(limit_text)s",
                            preFill: tags_as_string,
                            queryParam: 'q',
                            retrieveLimit: %(retrieve_limit)d,
                            minChars: 1,
                            neverSubmit: true,
                            extraParams: "&language=" + tab_lang
                        });
                    }

                    $('.as-selections').addClass('vTextField');
                    $('ul.as-selections li.as-original input').addClass('vTextField');

                    $('#%(result_id)s').parents().find('form').submit(function (){
                        tags_as_string = $("#as-values-%(widget_id)s").val();
                        $("#%(widget_id)s").remove();
                        tags_as_string = formatToJSON(tab_lang, tags_as_string);
                        $("#%(result_id)s").val(tags_as_string);
                    });
                });
            })(django.jQuery);
            </script>""" % {
                'result_id': result_attrs['id'],
                'widget_id': widget_attrs['id'],
                'url': autosuggest_url,
                'start_text': _("Enter Tag Here"),
                'empty_text': _("No Results"),
                'limit_text': _('No More Selections Are Allowed'),
                'retrieve_limit': MAX_SUGGESTIONS,
            }
        return result_html + widget_html + mark_safe(js)

    class Media:
        css_filename = getattr(settings, 'TAGGIT_AUTOSUGGEST_CSS_FILENAME',
            'autoSuggest.css')
        js_base_url = getattr(settings, 'TAGGIT_AUTOSUGGEST_STATIC_BASE_URL',
            '%sjquery-autosuggest' % settings.STATIC_URL)
        css = {
            'all': ('%s/css/%s' % (js_base_url, css_filename),)
        }
        js = (
            'admin/js/jquery.init.js',
            '%s/js/jquery.autoSuggest.minified.js' % js_base_url,
        )
