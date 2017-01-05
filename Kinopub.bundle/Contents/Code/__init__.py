# -*- coding: utf-8 -*-

import kinopub_api
import kinopub_settings
#import kinopub_http as KHTTP
import urllib2
import urllib
import demjson as json
import time
import sys
sys.setdefaultencoding("utf-8")

VERSION = "1.1.4"
VERSION_CHECK = "http://api.service-kp.com/plugins/plex/last"

ICON                = 'icon-default.png'
ART                 = 'art-default.jpg'
ICON                = 'icon-default.png'
PREFS               = 'icon-prefs.png'
SEARCH              = 'icon-search.png'

PREFIX = '/video/kinopub'

settings = kinopub_settings.Settings(Dict, storage_type="dict")
kpubapi = kinopub_api.API(settings, HTTPHandler=HTTP)

ITEM_URL = kinopub_api.API_URL + '/items'
ITEMS_PER_PAGE = 19

STATUS_WATCHED = 1
STATUS_UNWATCHED = -1
STATUS_STARTED = 0

####################################################################################################
def update_device_info(force=False):
    last_update = settings.get('device_info_update')
    if force or (not last_update or int(last_update) + 1800 < int(float(time.time()))):
        try:
            title = "PlexMediaServer"
            version = ""
            try:
                node = XML.ObjectFromURL("http://%s:%s/" % (Network.Address, 32400));
                title = node.attrib['friendlyName']
                version = "(%s)" % node.attrib['version']
            except:
                pass
            kpubapi.api_request('device/notify', params={
                'title': title,
                'hardware': "%s (%s)" % (Platform.OS, Platform.CPU),
                'software': "PlexMediaServer %s" % version,
            }, method="POST")
            settings.set('device_info_update', str(int(float(time.time()))))
        except:
            pass


def Start():
    update_device_info()
    Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')
    Plugin.AddViewGroup('List', viewMode='List', mediaType='items')

    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = 'kino.pub'

    DirectoryObject.thumb = R(ICON)
    NextPageObject.thumb = R(ICON)

    PrefsObject.thumb = R(PREFS)
    PrefsObject.art = R(ART)

    InputDirectoryObject.thumb = R(SEARCH)
    InputDirectoryObject.art = R(ART)

    HTTP.CacheTime = CACHE_1HOUR


def ValidatePrefs():
    return

def authenticate():
    def show_device_code():
        def verify_code():
            start_time = time.time()
            while True:
                if int(time.time() - start_time) > 5:
                    start_time = time.time()
                    status, response = kpubapi.get_access_token()
                    if status == kpubapi.STATUS_SUCCESS:
                        update_device_info(force=True)
                        return True

        status, response = kpubapi.get_device_code()
        if status == kpubapi.STATUS_SUCCESS:
            Thread.Create(verify_code)
            return MessageContainer("Активация устройства", "%s\nПосетите %s для активации устройства" % (settings.get('user_code'),settings.get('verification_uri')))
        return MessageContainer("Ошибка", "Произошла ошибка при обновлении кода устройства, перезапустите плагин 111.")


    auth_status = kpubapi.is_authenticated()
    if auth_status:
        return True
    elif auth_status == None:
        return MessageContainer("Ошибка", "Произошла ошибка при обращении к серверу. Попробуйте повторить запрос позже.")
    else:
        # check if we have refresh token
        if settings.get('refresh_token'):
            status, response = kpubapi.get_access_token(refresh=True)
            if status == kpubapi.STATUS_SUCCESS:
                return True
            if response.get('status') == 400:
                #kpubapi.reset_settings()
                return show_device_code()
            return MessageContainer("Ошибка", "Произошла ошибка при обращении к серверу. Попробуйте повторить запрос позже.")

        return show_device_code()

def show_videos(oc, items):
    video_clips = {}
    @parallelize
    def load_items():
        for num in xrange(len(items)):
            item = items[num]

            @task
            def load_task(num=num, item=item, video_clips=video_clips):
                if item['type'] not in ['serial', 'docuserial', 'tvshow'] and item['subtype'] != "multi":
                    # create playable item
                    li = VideoClipObject(
                        url = "%s/%s?access_token=%s#video=1" % (ITEM_URL, item['id'], settings.get('access_token')),
                        title = item['title'],
                        year = int(item['year']),
                        #rating = float(item['rating']),
                        summary = str(item['plot']),
                        genres = [x['title'] for x in item['genres']],
                        countries = [x['title'] for x in item['countries']],
                        content_rating = item['rating'],
                        #duration = int(videos[0]['duration'])*1000,
                        thumb = Resource.ContentsOfURLWithFallback(item['posters']['medium'], fallback=R(ICON))
                    )

                    try:
                        li.directors.clear()
                        li.roles.clear()
                        for d in item['director'].split(','):
                            li.directors.add(d.strip())
                        for a in item['cast'].split(','):
                            role = li.roles.new()
                            role.title = a.strip()
                            role.role = "Актёр"
                            li.roles.add(li)
                    except:
                        pass
                else:
                    # create directory for seasons and multiseries videos
                    li = DirectoryObject(
                        key = Callback(View, title=item['title'], qp={'id': item['id']}),
                        title = item['title'],
                        summary = item['plot'],
                        thumb = Resource.ContentsOfURLWithFallback(item['posters']['medium'], fallback=R(ICON))
                    )
                video_clips[num] = li

    for key in sorted(video_clips):
        oc.add(video_clips[key])

    return oc

def show_pagination(oc, pagination, qp, title="", callback=None):
        # Add "next page" button
        if callback is None:
            callback = Items

        if (int(pagination['current'])) + 1 <= int(pagination['total']):
            qp['page'] = int(pagination['current'])+1
            li = NextPageObject(
                key = Callback(callback, title=title, qp=qp),
                title = unicode('Еще...')
            )
            oc.add(li)

####################################################################################################
@handler(PREFIX, 'kino.pub', thumb=ICON, art=ART)
def MainMenu():
    result = authenticate()
    if not result == True:
        return result

    objects = [
        PrefsObject(title=u'Настройки', thumb=R(PREFS)),
        InputDirectoryObject(
            key     = Callback(Search, qp={}),
            title   = unicode('Поиск'),
            prompt  = unicode('Поиск')
        ),
        DirectoryObject(
            key = Callback(Tv, title='ТВ', qp={}),
            title = unicode('ТВ')
        ),
        DirectoryObject(
            key = Callback(Watching, title='Новые эпизоды', qp={}),
            title = unicode('Новые эпизоды (%s)' % get_unwatched_count())
        ),
        DirectoryObject(
            key = Callback(Collections, title='Подборки', qp={}),
            title = unicode('Подборки')
        ),
        DirectoryObject(
            key = Callback(Items, title='Последние', qp={}),
            title = unicode('Последние'),
            summary = unicode('Все фильмы и сериалы отсортированные по дате добавления/обновления.')
        ),
        DirectoryObject(
            key = Callback(Items, title='Популярные', qp={'sort':'-rating'}),
            title = unicode('Популярные'),
            summary = unicode('Все фильмы и сериалы отсортированные по рейтингу.')
        ),
        DirectoryObject(
            key = Callback(Bookmarks, title='Закладки', qp={}),
            title = unicode('Закладки'),
        ),
    ]

    version = check_version()
    if version:
        objects.insert(0, DirectoryObject(
            key = None,
            title = unicode(version),
            summary = unicode("Скачайте обновление на странице http://kino.pub/plugins/plex")
        ))

    oc = ObjectContainer(
        view_group = 'InfoList',
        objects = objects,
    )

    response = kpubapi.api_request('types')
    if response['status'] == 200:
        for item in response['items']:
            li = DirectoryObject(
                key = Callback(Types, title=item['title'], qp={'type': item['id']}),
                title = unicode(item['title']),
                summary = unicode(item['title'])
            )
            oc.add(li)
    else:
        return MessageContainer("Ошибка %s" % response['status'], response['message'])
    return oc
'''
  Next screen after MainMenu.
  Show folders:
    - Search
    - Latest (sort by date/update)
    - Rating (sort by rating)
    - Genres
'''
@route(PREFIX + '/Types', qp=dict)
def Types(title, qp=dict):
    result = authenticate()
    if not result == True:
        return result

    oc = ObjectContainer(
        view_group = 'InfoList',
        objects = [
            InputDirectoryObject(
                key     = Callback(Search, qp=qp),
                title   = unicode('Поиск'),
                prompt  = unicode('Поиск')
            ),
            DirectoryObject(
                key = Callback(Items, title='Последние', qp=merge_dicts(qp, dict({'sort': '-updated'}))),
                title = unicode('Последние'),
                summary = unicode('Отсортированные по дате добавления/обновления.')
            ),
            DirectoryObject(
                key = Callback(Items, title='Популярные', qp=merge_dicts(qp, dict({'sort': '-rating'}))),
                title = unicode('Популярные'),
                summary = unicode('Отсортированные по рейтингу')
            ),
            DirectoryObject(
                key = Callback(Alphabet, title='По алфавиту', qp=qp),
                title = unicode('По алфавиту'),
                summary = unicode('Отсортированные по буквам алфавита.')
            ),
            DirectoryObject(
                key = Callback(Genres, title='Жанры', qp=qp),
                title = unicode('Жанры'),
                summary = unicode('Список жанров')
            ),
        ]
    )
    return oc

'''
  Called from Types route.
  Display genres for media type
'''
@route(PREFIX + '/Genres', qp=dict)
def Genres(title, qp=dict):
    result = authenticate()
    if not result == True:
        return result

    response = kpubapi.api_request('genres', params={'type': qp['type']})
    oc = ObjectContainer(view_group='InfoList')
    if response['status'] == 200:
        for genre in response['items']:
            li = DirectoryObject(
                key = Callback(Items, title=genre['title'], qp={'type':qp['type'], 'genre': genre['id']}),
                title = genre['title'],
            )
            oc.add(li)
    return oc

'''
  Shows media items.
  Items are filtered by 'qp' param.
  See http://kino.pub/docs/api/v2/api.html#video
'''
@route(PREFIX + '/Items', qp=dict)
def Items(title, qp=dict):
    result = authenticate()
    if not result == True:
        return result

    qp['perpage'] = ITEMS_PER_PAGE
    response = kpubapi.api_request('items', qp)
    oc = ObjectContainer(title2=unicode(title), view_group='InfoList')
    if response['status'] == 200:
        show_videos(oc, response['items'])
        show_pagination(oc, response['pagination'], qp, title=title)
    return oc

'''
  Display serials or multi series movies
'''
@route(PREFIX + '/View', qp=dict)
def View(title, qp=dict):
    result = authenticate()
    if not result == True:
        return result

    response = kpubapi.api_request('items/%s' % int(qp['id']))
    if response['status'] == 200:
        item = response['item']
        show_title = item['title']
        show_title = show_title.split(" / ");
        if len(show_title) > 1:
            show_title = show_title[1]
        else:
            show_title = show_title[0]
        # prepare serials
        if item['type'] in ['serial', 'docuserial', 'tvshow']:
            oc = ObjectContainer(title1=show_title,title2=unicode(title), view_group='InfoList')
            watch_info = kpubapi.api_request("watching", {'id': qp['id']}, cacheTime=0)['item']
            if 'season' in qp:
                for season in item['seasons']:
                    if int(season['number']) == int(qp['season']):
                        watch_season = watch_info['seasons'][int(season['number'])-1]
                        for episode_number, episode in enumerate(season['episodes']):
                            watch_episode = watch_season['episodes'][episode_number]
                            episode_number += 1
                            # create playable item
                            episode_title = "%s" % episode['title'] if len(episode['title']) > 1 else "Эпизод %s" % episode_number
                            episode_title = "s%02de%02d. %s"  % (season['number'], episode_number, episode_title)
                            watch_title = ""
                            if watch_episode['status'] == 1:
                                watch_title = "✓"
                            elif watch_episode['status'] == 0:
                                watch_title = "➤"
                            else:
                                watch_title = "✕"

                            episode_title = "%s %s" % (watch_title, episode_title)

                            li = EpisodeObject(
                                url = "%s/%s?access_token=%s#season=%s&episode=%s" % (ITEM_URL, item['id'], settings.get('access_token'), season['number'], episode_number),
                                title = unicode(episode_title),
                                index = episode_number,
                                rating_key = episode['id'],
                                show = show_title,
                                duration = int(episode['duration'])*1000,
                                thumb = Resource.ContentsOfURLWithFallback(episode['thumbnail'], fallback=R(ICON))
                            )
                            oc.add(li)
                        break
            else:
                for season in item['seasons']:
                    watch_season = watch_info['seasons'][int(season['number'])-1]
                    watch_title = ""
                    if watch_season['status'] == 1:
                        watch_title = "✓"
                    elif watch_season['status'] == 0:
                        watch_title = "➤"
                    else:
                        watch_title = "✕"
                    season_title = season['title'] if season['title'] and len(season['title']) > 2 else "Сезон %s" % int(season['number'])
                    season_title = "%s %s" % (watch_title, season_title)
                    test_url = item['posters']['medium']
                    li = DirectoryObject(
                        key = Callback(View, title=season_title, qp={'id': item['id'], 'season': season['number']}),
                        title = unicode(season_title),
                        thumb = Resource.ContentsOfURLWithFallback(season['episodes'][0]['thumbnail'].replace('dev.',''), fallback=R(ICON))
                    )
                    oc.add(li)
        #prepare movies, concerts, 3d
        elif 'videos' in item and len(item['videos']) > 1:
            oc = ObjectContainer(title1=show_title,title2=unicode(title), view_group='InfoList')
            for video_number, video in enumerate(item['videos']):
                video_number += 1
                # create playable item
                li = EpisodeObject(
                    url = "%s/%s?access_token=%s#video=%s" % (ITEM_URL, item['id'], settings.get('access_token'), video_number),
                    title = video['title'],
                    index = video_number,
                    rating_key = video['id'],
                    duration = int(video['duration']) * 1000,
                    thumb = Resource.ContentsOfURLWithFallback(video['thumbnail'], fallback=R(ICON)),
                )
                oc.add(li)
        else:
            oc = ObjectContainer(title1=show_title,title2=unicode(title), view_group='InfoList')
            video = item['videos'][0]
            video_number = 1
            li = MovieObject(
                url = "%s/%s?access_token=%s#video=%s" % (ITEM_URL, item['id'], settings.get('access_token'), video_number),
                title = item['title'],
                rating_key = item['id'],
                year = int(item['year']),
                summary = str(item['plot']),
                genres = [x['title'] for x in item['genres']] if item['genres'] else [],
                countries = [x['title'] for x in item['countries']] if item['countries'] else [],
                content_rating = item['rating'],
                thumb = Resource.ContentsOfURLWithFallback(video['thumbnail'], fallback=R(ICON))
            )

            try:
                li.directors.clear()
                li.roles.clear()
                for d in item['director'].split(','):
                    li.directors.add(d.strip())
                for a in item['cast'].split(','):
                    role = li.roles.new()
                    role.title = a.strip()
                    role.role = "Актёр"
                    li.roles.add(li)
            except:
                pass

            oc.add(li)
    return oc

'''
  Search items
'''
@route(PREFIX + '/Search', qp=dict)
def Search(query, qp=dict):
    result = authenticate()
    if not result == True:
        return result

    if qp.get('id'):
        del qp['id']

    return Items('Поиск', qp=merge_dicts(qp, dict({'title' : query, 'perpage': ITEMS_PER_PAGE})))


'''
  Alphabet
'''
@route(PREFIX + '/Alphabet', qp=dict)
def Alphabet(title, qp):
    result = authenticate()
    if not result == True:
        return result

    alpha = [
        "А,Б,В,Г,Д,Е,Ё,Ж,З,И,Й,К,Л,М,Н,О,П,Р,С,Т,У,Ф,Х,Ц,Ч,Ш,Щ,Ы,Э,Ю,Я",
        "A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z"
    ]

    oc = ObjectContainer(title2=unicode(title), view_group='InfoList')
    for al in alpha:
        letters = al.split(",")
        for letter in letters:
            li = DirectoryObject(
                    key = Callback(Items, title=letter, qp=merge_dicts(qp, {'letter': letter})),
                title = unicode(letter)
            )
            oc.add(li)
    return oc

'''
  Bookmarks
'''
@route(PREFIX + '/Bookmarks', qp=dict)
def Bookmarks(title, qp):
    result = authenticate()
    if not result == True:
        return result

    oc = ObjectContainer(title2=unicode(title), view_group='InfoList')
    if 'folder-id' not in qp:
        response = kpubapi.api_request('bookmarks', qp, cacheTime=0)
        if response['status'] == 200:
            Log("TOTAL BOOKMARKS = %s" % len(response['items']))
            for folder in response['items']:
                Log(folder['title'])
                li = DirectoryObject(
                    key = Callback(Bookmarks, title=folder['title'].encode('utf-8'), qp={'folder-id': folder['id']}),
                    title = unicode(folder['title']),
                )
                oc.add(li)
    else:
        response = kpubapi.api_request('bookmarks/%s' % qp['folder-id'], qp, cacheTime=0)
        if response['status'] == 200:
            show_videos(oc, response['items'])
            show_pagination(oc, response['pagination'], qp, title=title, callback=Bookmarks)
    return oc


@route(PREFIX + '/Watching', qp=dict)
def Watching(title, qp=dict):
    result = authenticate()
    if not result == True:
        return result

    oc = ObjectContainer(title2=unicode(title), view_group='InfoList')
    if 'new' not in qp:
        response = kpubapi.api_request('watching/serials', params={'subscribed': 1}, cacheTime=60)
        if response['status'] == 200:
            for item in response['items']:
                li = DirectoryObject(
                    #key = Callback(Watching, title=item['title'], qp={'id': item['id'], 'new': item['new']}),
                    key = Callback(View, title=item['title'], qp={'id': item['id']}),
                    title = item['title'] + ' (%s)' % item['new'],
                    thumb = Resource.ContentsOfURLWithFallback(item['posters']['medium'], fallback=R(ICON))
                )
                oc.add(li)
            #oc.objects.sort(key = lambda obj: obj.title)
    return oc

@route(PREFIX + '/Collections', qp=dict)
def Collections(title, qp=dict):
    result = authenticate()
    if not result == True:
        return result

    oc = ObjectContainer(title2=unicode(title), view_group='InfoList', )
    if 'id' not in qp:
        objects = [            
            DirectoryObject(
                key = Callback(Collections, title='Последние', qp=merge_dicts(qp, {'sort': '-created'})),
                title = unicode('Последние')
            ),
            DirectoryObject(
                key = Callback(Collections, title='Просматриваемые', qp=merge_dicts(qp, {'sort': '-watchers'})),
                title = unicode('Просматриваемые')
            ),
            DirectoryObject(
                key = Callback(Collections, title='Популярные', qp=merge_dicts(qp, {'sort': '-views'})),
                title = unicode('Популярные')
            ),
        ]
        oc.objects = objects
        response = kpubapi.api_request('collections', qp)
        if response['status'] == 200:
            for item in response['items']:
                li = DirectoryObject(
                    #key = Callback(Watching, title=item['title'], qp={'id': item['id'], 'new': item['new']}),
                    key = Callback(Collections, title=item['title'], qp={'id': item['id']}),
                    title = item['title'],
                    thumb = Resource.ContentsOfURLWithFallback(item['posters']['medium'], fallback=R(ICON))
                )
                oc.add(li)
            Log.Exception("Pag: %s " % qp)
            show_pagination(oc, response['pagination'], qp, title=title, callback=Collections)
    else:
        response = kpubapi.api_request('collections/view', qp)
        if response['status'] == 200:
            for item in response['items']:
                li = DirectoryObject(
                    #key = Callback(Watching, title=item['title'], qp={'id': item['id'], 'new': item['new']}),
                    key = Callback(View, title=item['title'], qp={'id': item['id']}),
                    title = item['title'],
                    thumb = Resource.ContentsOfURLWithFallback(item['posters']['medium'], fallback=R(ICON))
                )
                oc.add(li)
    return oc

@indirect
def PlayVideo(url):
    return IndirectResponse(VideoClipObject, key=url)

@route(PREFIX + '/Tv', qp=dict)
def Tv(title, qp=dict, include_container=False):
    result = authenticate()
    if not result == True:
        return result

    oc = ObjectContainer(title2=unicode(title), view_group='InfoList')
    response = kpubapi.api_request('tv/index', cacheTime=320)

    if response['status'] == 200:
        for ch in response['channels']:
            li = VideoClipObject(
                key = Callback(Tv, title=ch['title'], qp={'id' : ch['id']}, include_container=True),
                rating_key = ch['stream'],
                title = ch['title'],
                thumb = Resource.ContentsOfURLWithFallback(ch['logos']['s'], fallback='icon-default.png'),
                items = [
                    MediaObject(
                        parts = [
                            PartObject(key=Callback(PlayVideo, url=ch['stream']))
                        ],
                        protocol = 'hls',
                        audio_codec = AudioCodec.AAC,
                        container = Container.MP4,
                        video_codec = VideoCodec.H264
                    )
                ]
            )

            if 'id' in qp and qp['id'] == ch['id']:
                if include_container:
                    return ObjectContainer(objects=[li])
            else:
                oc.add(li)
    return oc

####################
def merge_dicts(*args):
    result = {}
    for d in args:
        result.update(d)
    return result

def check_version():
    version = HTTP.Request(VERSION_CHECK, cacheTime=3600)
    if VERSION.strip() != str(version).strip():
        return "Доступна новая версия! %s => %s" % (VERSION, version)
    return ""

def get_unwatched_count():
    result = authenticate()
    if not result == True:
        return result

    count = 0
    response_serials = kpubapi.api_request('watching/serials',params={'subscribed': 1}, cacheTime=60)
    if response_serials['status'] == 200:
        for serial in response_serials['items']:
            count += serial['new']
    return count

