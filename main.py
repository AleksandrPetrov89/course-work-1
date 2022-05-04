import requests
# from pprint import pprint
import datetime
import json
from tqdm import tqdm
import os


class Uploader:
    """ Класс Uploader предназначен для создания каталогов и загрузки файлов на Яндекс.диск.

        ya_token - OAuth-токен, полученный с полигона Яндекс.диска.

    """

    def __init__(self, ya_token: str):
        self.ya_token = ya_token
        self.ya_url = 'https://cloud-api.yandex.net/v1/disk/resources'

    def ya_create_folder(self, path: str):
        """ Создает каталог(папку) на Яндекс.диске с именем 'path'.

            :param path: строка, с именем каталога(папки), который хотим создать.

            При указании в 'path' только имени каталога, создает папку в корневой директории Яндекс.диска.
            Если в 'path' указать  путь, куда хотим создать и имя папки, в формате 'путь/имя' - папка
            создастся в указанной директории.

        """
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json',
                   'Authorization': self.ya_token}
        params = {'path': path}
        requests.put(self.ya_url, params=params, headers=headers)

    def ya_upload(self, path: str, downloadable_url: str):
        """ Загружает на Яндекс.диск файл с именем 'path' по ссылке на файл 'downloadable_url'.

            :param path: Полное имя файла, который загружаем, в формате 'путь/имя'.
                           Если указать только имя - загрузит файл в корневую директорию Яндекс.диска.

            :param downloadable_url: Внешняя ссылка на файл, который хотим загрузить

        """
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json',
                   'Authorization': self.ya_token}
        params = {'path': path, 'url': downloadable_url}
        url = f"{self.ya_url}/upload"
        requests.post(url, params=params, headers=headers)

    def google_create_folder(self):
        pass


class VkPhotoCopier(Uploader):
    """ Класс VkPhotoCopier предназначен для поиска и загрузки на Яндекс.диск фотографий и альбомов
        из профиля пользователя 'ВКонтакте'.

        vk_id - Id пользователя 'ВКонтакте'.

        vk_token - Токен, для работы в API ВКонтакте.

        ya_token - OAuth-токен, полученный с полигона Яндекс.диска.

        version_api - Версия API ВКонтакте. По умолчанию 5.131 - т.к. является текущей.

    """

    def __init__(self, vk_id: str, vk_token: str, ya_token: str, version_api: float = 5.131):
        super().__init__(ya_token=ya_token)
        self.vk_id = vk_id
        self.vk_token = vk_token
        self.version_api = version_api
        self.vk_url = 'https://api.vk.com/method/'

    def vk_album_search(self, number_albums: int) -> list:
        """ Производит поиск информации по альбомам фотографий, находящимся в свободном доступе.

            :param number_albums: Количество альбомов, которое мы хотим найти.

            :return: Возвращает список альбомов в виде словарей.
                       Формат списка:  [{'album_id': id альбома_1, 'title': 'Название альбома_1'},
                                        {'album_id': id альбома_2, 'title': 'Название альбома_2'},
                                         ...

                                        {'album_id': id альбома_n, 'title': 'Название альбома_n'}]

            Если альбомов в свободном доступе нет, то возвращает пустой список.

        """
        if number_albums == 0:
            number_albums = ''
        else:
            number_albums = str(number_albums)
        url = self.vk_url + 'photos.getAlbums'
        params = {'owner_id': self.vk_id, 'count': number_albums,
                  'access_token': self.vk_token, 'v': self.version_api}
        resp = requests.get(url, params=params)
        albums = []
        if resp.json()['response']['count'] > 0:
            data = resp.json()['response']['items']
            for album in data:
                albums += [{'album_id': album['id'], 'title': album['title']}]
        # pprint(albums)
        return albums

    def vk_get_info_photo(self, number_photos: int, album_id: str = 'profile'):
        """ Производит поиск информации по фотографиям пользователя ВКонтакте,
            находящимся в свободном доступе из определенного альбома.

            :param number_photos: Количество фотографий, которое нас интересует.

            :param album_id: Id альбома, который нас интересует. По умолчанию используется
                               альбом с фотографиями профиля.

            :return: Возвращает список фотографий в виде словарей.
                       Формат списка: [{'album_id': номер фльбома,
                                        'date': Unix дата загрузки фото_1,
                                        'height': высота_1(в пикселях),
                                        'id': номер фото_1,
                                        'likes': кол-во лайков_1,
                                        'sizes': тип размера_1,
                                        'url': 'ссылка_1',
                                        'width': ширина_1(в пикселях)},
                                       ...]

            У каждой найденной фотографии проводит поиск варианта фотографии с наибольшим размером.
            Возвращается информация именно по копии с максимальным размером.

        """
        url = self.vk_url + 'photos.get'
        params = {'owner_id': self.vk_id, 'album_id': album_id, 'extended': 1, 'photo_sizes': 1,
                  'count': number_photos, 'access_token': self.vk_token, 'v': self.version_api}
        resp = requests.get(url, params=params)
        data = resp.json()['response']['items']
        info_photos = []
        for photo in data:
            max_size = []
            info_photo = {'id': photo['id'], 'album_id': photo['album_id'],
                          'date': photo['date'], 'likes': photo['likes']['count']}
            size_types = ('w', 'z', 'y', 'x', 'r', 'q', 'p', 'o', 'm', 's')
            for size_type in size_types:
                max_size = list(filter(lambda size: size_type in size['type'], photo['sizes']))
                if max_size:
                    break
            info_photo.update(url=max_size[0]['url'], sizes=max_size[0]['type'],
                              height=max_size[0]['height'], width=max_size[0]['width'])
            info_photos += [info_photo]
        # pprint(info_photos)
        return info_photos

    def vk_uploader(self, path: str, photos: list, album_name: str):
        """ Отправляет на загрузку на Яндекс.диск в указанную папку, полученный список фотографий.

            :param path: Путь к директории, куда нужно загрузить фотографии.

            :param photos: Список фотографий, которые необходимо отправить на загрузку.
                           Формат списка: [{'album_id': номер фльбома,
                                            'date': Unix дата загрузки фото_1,
                                            'height': высота_1(в пикселях),
                                            'id': номер фото_1,
                                            'likes': кол-во лайков_1,
                                            'sizes': тип размера_1,
                                            'url': 'ссылка_1',
                                            'width': ширина_1(в пикселях)},
                                             ...]

            :param album_name: Название альбома к которому принадлежат фотографии.

            :return: Возвращает список файлов, отправленных на загрузку.
                     Формат списка: [{'file_name': 'имя файла 1', 'size': 'тип размера файла 1'},
                                     {'file_name': 'имя файла 2', 'size': 'тип размера файла 2'},
                                     ...,
                                     {'file_name': 'имя файла n', 'size': 'тип размера файла n'}]

            Каждой фотографии присваивается имя, соответствующее количеству лайков за эту фотографию.
            Если количество лайков у фотографий из списка совпадает, то к имени последующих фотографий
            с таким же количеством лайков добавляется дата загрузки этой фотографии.

        """
        names_photo = []
        result = []
        for photo in tqdm(photos, desc=album_name, position=0, leave=True):
            file_name = str(photo['likes'])
            if file_name in names_photo:
                created = datetime.datetime.fromtimestamp(photo['date']).strftime('%Y-%m-%d %H-%M-%S')
                file_name += f" {created}"
            names_photo += [file_name]
            file_name += '.jpg'
            path_file = f"{path}/{file_name}"
            url_photo = photo['url']
            self.ya_upload(path_file, url_photo)
            result += [{'file_name': file_name, 'size': photo['sizes']}]
        # pprint(result)
        return result

    def vk_backup_photo(self, other_albums: bool = False, number_albums: int = 0, number_photos: int = 5):
        """ Производит резервное копирование общедоступных фотографий из профиля ВКонтакте на Яндекс.диск.

        :param other_albums: Нужно ли копировать фото из других альбомов. По умолчанию = False.

        :param number_albums: Количество других альбомов, которые нужно скопировать.
                              По умолчанию, если параметр "other_albums=True", происходит копирование
                              по всем общедоступным альбомам.
                              При указании значения отличного от нуля - поиск ограничивается указанным
                              количеством альбомов, а параметр "other_albums" автоматически меняется на "True".

        :param number_photos: Количество фотографий, которое нужно скопировать. При копировании не только
                              фотографий профиля, но и альбомов - из каждого альбома будет скопированно,
                              указанное количество фотографий. По умолчанию = 5 шт.

        На Яндекс.диске в корневой директории создается папка с названием "VK backup photo + текущая дата и время".
        В нее происходит копирование фотографий из профиля ВКонтакте.
        Если производится копирование и из других альбомов, то в папке "VK backup photo + текущая дата и время"
        создаются папки с названием копируемых альбомов, и уже в них копируются соответствующие фотографии.

        Также, в текущей директории создается папка с названием 'result', в нее сохраняется информация по
        скопированным фотографиям в виде json-файла.
        Формат файла: {"profile": [{"file_name": "имя файла 1", "size": "тип размера файла 1"},
                                   ...,
                                   {"file_name": "имя файла n", "size": "тип размера файла n"}],
                       "Название альбома 1": [{"file_name": "имя файла 1", "size": "тип размера файла 1"},
                                              ...,
                                              {"file_name": "имя файла n", "size": "тип размера файла n"}],
                       "Название альбома n": [{"file_name": "имя файла 1", "size": "тип размера файла 1"},
                                              ...,
                                              {"file_name": "имя файла n", "size": "тип размера файла n"}]
                        }

        :return: None

        """
        if number_albums != 0:
            other_albums = True
        result = {}
        date_time = datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S')
        path = f'VK backup photo {date_time}'
        self.ya_create_folder(path=path)
        photos = self.vk_get_info_photo(number_photos=number_photos)
        result['profile'] = self.vk_uploader(path=path, photos=photos, album_name='profile')

        if other_albums is True:
            albums = self.vk_album_search(number_albums=number_albums)
            if albums:
                for album in tqdm(albums, desc='other albums', position=0, leave=True):
                    path_album = f"{path}/{album['title']}"
                    self.ya_create_folder(path=path_album)
                    photos = self.vk_get_info_photo(number_photos=number_photos, album_id=album['album_id'])
                    result[album['title']] = self.vk_uploader(path=path_album, photos=photos, album_name=album['title'])
        folder = 'result'
        if os.path.exists(folder) is False:
            os.mkdir(folder)
        file_name = f"result vk_backup_photo {date_time}.json"
        file_path = os.path.join(folder, file_name)
        with open(file_path, 'w', encoding='utf-8') as result_file:
            json.dump(result, result_file, ensure_ascii=False)


if __name__ == '__main__':
    user_vk_id = '552934290'
    token_vk = ''
    token_ya_disk = ''

    user = VkPhotoCopier(vk_id=user_vk_id, vk_token=token_vk, ya_token=token_ya_disk)
    user.vk_backup_photo()
