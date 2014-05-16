import json
from collections import Counter
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from analysis.models import MusicData, Composition
from analysis.computation.range import range_analysis


def home(request):
    return render(request, "index.html")


def login_user(request):
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect('/')
            else:
                return render(request, "login_user.html", {'error': True})
        else:
            return render(request, "login_user.html", {'error': True})

    else:
        return render(request, 'login_user.html')


def dashboard(request):
    music_data_count = MusicData.objects.count()
    composition_count = Composition.objects.count()
    args = {'music_data_count': music_data_count,
            'composition_count': composition_count}
    return render(request, "dashboard.html", args)


def show_range(request):
    def uniq_items_in_model(item, model=MusicData):
        items = model.objects.values(item).distinct().order_by(item)
        return [x[item] for x in items]

    def select_filter(name, item, arguments, template='music_data__%s'):
        if item != "all":
            arguments[template % name] = item

    if request.method == 'POST':
        kwargs = {}

        title = request.POST['select-composition']
        key = request.POST['select-key']
        total_duration = request.POST['select-duration']
        time_signature = request.POST['select-time-signature']

        select_filter('title', title, kwargs, template='%s')
        select_filter('key', key, kwargs)
        select_filter('total_duration', total_duration, kwargs)
        select_filter('time_signature', time_signature, kwargs)

        compositions = Composition.objects.filter(**kwargs)
        result = range_analysis(compositions)

        args = {'result': result}
        return render(request, 'range_result.html', args)

    args = {'compositions': uniq_items_in_model('title', Composition),
            'keys': uniq_items_in_model('key'),
            'durations': uniq_items_in_model('total_duration'),
            'signatures': uniq_items_in_model('time_signature'),
    }
    return render(request, 'range.html', args)


def d3(request):
    args = {}
    return render(request, 'd3.html', args)


def range_data(request):
    compositions = Composition.objects.all()
    range_list = [c.music_data.ambitus for c in compositions]
    frequency = Counter(range_list)
    values = [{"label": k, "value": v} for k, v in sorted(frequency.items())]

    data = [
        {
            "key": "Quantity",
            "bar": True,
            "color": "#ccf",
            "values": values
        }]

    return HttpResponse(json.dumps(data), mimetype="application/javascript")
