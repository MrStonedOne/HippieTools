import json
import time

from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from hippie_ss13.models import Player
from hippie_banevasion import models
from hippie_banevasion.utils import utils
from hippie_banevasion.mixins import ComesFromGameserver, HasBody
from .. import enums

class GetProtectedDataView(ComesFromGameserver, View):
    def get(self, request, *args, **kwargs):
        data = request.GET.get('body', '')
        if data == '':
            raise Http404()

        data_obj = json.loads(data)
        data_obj['time'] = time.time()
        data = json.dumps(data_obj)

        blob = utils.encode_encrypt_data(data)

        response = HttpResponse(blob, content_type='text/plain')
        response['Content-Length'] = len(blob)
        return response

class GetAlts(ComesFromGameserver, View):
    def get(self, request, *args, **kwargs):
        ckey = request.GET.get('ckey', '')
        if ckey == '':
            raise Http404()

        alt_list = {}

        try:
            client = models.Client.objects.get(ckey=ckey)
            alts = client.get_alts()
            for alt in alts:
                alt_list[alt.get_ckey()] = alt.get_player().get_standing()
        except models.Client.DoesNotExist:
            pass

        player = Player.objects.get(ckey=ckey)
        ip_alts = player.get_ip_alts()
        cid_alts = player.get_cid_alts()
        ip_cid_alts = set(ip_alts) - (set(ip_alts) - set(cid_alts))

        for alt in ip_cid_alts:
            alt_list[alt.ckey] = alt.get_standing()

        data = json.dumps(alt_list)

        response = HttpResponse(data, content_type='text/plain')
        response['Content-Length'] = len(data)
        return response


@method_decorator(xframe_options_exempt, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class ClientView(HasBody, View):
    def get(self, request, *args, **kwargs):
        useragent = utils.get_useragent(request)

        data = request.GET.get('body', '')
        data_obj = utils.decode_encrypted_data(data)
        current_ckey = data_obj["ckey"]

        client_obj, created = models.Client.objects.get_or_create(ckey=current_ckey)
        if created is False:
            client_obj.last_seen = timezone.now()
            client_obj.save(update_fields=["last_seen"])

        if utils.check_sentry(request, client_obj):
            context = {"debug_mode": False, "client_blob": "debug"}
            return render(request, "hippie_banevasion/fake_client/client.html", context)

        if not utils.verify_encrypted_data(data_obj, 180, request, client_obj):
            utils.store_security_event(
                request,
                "invalid_data",
                client_obj,
                "payload: {}".format(data)
            )
            raise Http404()

        data_obj['time'] = time.time()
        data = json.dumps(data_obj)
        blob = utils.encode_encrypt_data(data)

        utils.store_useragent(useragent)
        utils.store_byondversion(data_obj['byond_version'])

        # BYOND Version
        byond_version = models.ByondVersion.objects.get(byondversion=data_obj['byond_version'])
        client_obj.byond_versions.add(byond_version)

        # Useragent
        useragent_obj = models.Useragent.objects.get(useragent_hash=utils.hash_ua(useragent))
        client_obj.useragents.add(useragent_obj)

        # IP Address
        client_obj.ips.add(request.ip_obj)

        context = {"debug_mode": False, "client_blob": blob}
        if utils.check_useragent(request, client_obj):
            print("Sending a real client to {}".format(client_obj.ckey))
            return render(request, "hippie_banevasion/real_client/client.html", context)
        else:
            print("Serving a false client to {}".format(client_obj.ckey))
            return render(request, "hippie_banevasion/fake_client/client.html", context)

    def post(self, request, *args, **kwargs):
        fingerprint_hash = request.POST.get('fp', '')
        current_payload = request.POST.get('cec', '')
        archived_payload = request.POST.get('aec', '')

        current_payload_obj = utils.decode_encrypted_data(current_payload)

        current_ckey = current_payload_obj["ckey"]
        client_obj, created = models.Client.objects.get_or_create(ckey=current_ckey)

        if not utils.verify_encrypted_data(current_payload_obj, 90, request, client_obj):
            utils.store_security_event(
                request,
                "invalid_data",
                client_obj,
                "payload: {}".format(current_payload)
            )
            raise Http404()

        if created is False:
            client_obj.last_seen = timezone.now()
            client_obj.save(update_fields=["last_seen"])

        # Fingerprint
        clblob, created = models.ClientBlob.objects.get_or_create(fingerprint=fingerprint_hash)
        client_obj.fingerprints.add(clblob)

        # IP Address
        client_obj.ips.add(request.ip_obj)

        # Evercookie
        if archived_payload != '':
            archived_payload_obj = utils.decode_encrypted_data(archived_payload)
            archived_ckey = archived_payload_obj["ckey"]

            if archived_ckey != current_ckey:
                msg = "{} is an alt of {}".format(archived_ckey, current_ckey)
                utils.store_security_event(
                    request,
                    "alt_detected",
                    client_obj,
                    msg
                )
                print(msg)
                alt_client_obj = models.Client.objects.get(ckey=archived_ckey)
                client_obj.related_accounts.add(alt_client_obj)

                if alt_client_obj.reverse_engineer:
                    msg = "Reverse Engineer alt account detected: {}".format(current_ckey)
                    utils.store_security_event(
                        request,
                        "associated_reverse_engineer",
                        client_obj,
                        msg
                    )
                    print(msg)
                    client_obj.reverse_engineer = True
                    client_obj.save(update_fields=["reverse_engineer"])

        # Lastpost
        client_obj.last_post = timezone.now()
        client_obj.save(update_fields=["last_post"])
        
        return HttpResponse('')
