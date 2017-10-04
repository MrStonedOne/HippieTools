from django.core.urlresolvers import reverse
from django.contrib.auth import logout
from django.http import HttpResponseRedirect, HttpResponseForbidden
from hippie_banevasion.models import Client, CKEY_TO_KEY_RE
from hippie_ss13.models import Player

def check_rank(get_response):
    def middleware(request):

        path = request.META['PATH_INFO'].rstrip("/")
        if path not in ["/accounts/login", "/accounts/xenforo/login", "/accounts/xenforo/login/callback"] and not request.user.is_authenticated():
            return HttpResponseRedirect("/accounts/login")

        ckey = request.user.username
        ckey = CKEY_TO_KEY_RE.sub('', ckey)
        request.current_player = Player.objects.get(ckey=ckey)

        if request.current_player.get_rank() not in ["Host", "GameMaster", "GameAdmin"]:
            logout(request)
            return HttpResponseForbidden("You should not be here!")

        response = get_response(request)
        return response

    return middleware