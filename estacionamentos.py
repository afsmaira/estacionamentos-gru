""" https://www.melhoresdestinos.com.br/estacionamento-aeroporto-guarulhos.html """
import re
import requests
import math
from datetime import datetime as dt2, timedelta
from bs4 import BeautifulSoup

import googlemaps
import configparser


cfg = configparser.ConfigParser()
cfg.optionxform = str
cfg.read('config.cfg')

api_key = cfg['Maps'].get('APIKey', None)
try:
    gmaps = googlemaps.Client(key=api_key)
except ValueError:
    gmaps = None
terminal = cfg['Maps'].get('terminal', '1')


def busca_local(maps, q):
    if maps is None:
        return
    try:
        return maps.find_place(q, 'textquery',
                               fields=["name"])['candidates'][0]['name']
    except googlemaps.exceptions.ApiError:
        return


def get_hiddens(txt):
    return dict(re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]+)">',
                           txt))


class Estacionamento:
    def __init__(self, ini, fim):
        print(f'Verificando {self.nome()}...')
        self.ini = dt2.strptime(ini, '%Y-%m-%d %H:%M')
        self.fim = dt2.strptime(fim, '%Y-%m-%d %H:%M')
        self.dt = self.fim - self.ini
        self.lista = []
        self.i = 0

    def __iter__(self):
        self.i = 0
        return self

    def __next__(self):
        if self.i < len(self.lista):
            r = self.lista[self.i]
            self.i += 1
            if len(r) == 2:
                r += ('',)
            else:
                r = r[:-1] + (' (' + r[-1] + ')',)
            return r[0], (str(self) + ' ' + r[1]).strip(), r[2]
        raise StopIteration

    def __str__(self):
        d = self.dist()
        t = self.tempo()
        r = self.nome()
        if len(d) > 0:
            r += f' ({d}, {t})'
        return r

    def geo(self):
        return busca_local(gmaps, self.nome())

    def busca(self):
        if self.busca_maps is None:
            if gmaps is None:
                return
            nome = self.geo()
            if nome is None:
                self.busca_maps = None
            else:
                self.busca_maps = gmaps.distance_matrix(nome, f'Terminal {terminal}, GRU')['rows'][0]['elements'][0]
                if self.busca_maps['status'] in {'ZERO_RESULTS', 'NOT_FOUND'}:
                    self.busca_maps = None
        return self.busca_maps

    def dist(self):
        b = self.busca()
        if b is None:
            return ''
        return b['distance']['text']

    def tempo(self):
        b = self.busca()
        if b is None:
            return ''
        return b['duration']['text']

    def nome(self):
        return self.__class__.__name__


class GRU(Estacionamento):
    def __init__(self, ini, fim, promo):
        super().__init__(ini, fim)
        if not isinstance(ini, int):
            ini = dt2.timestamp(self.ini)
        if not isinstance(fim, int):
            fim = dt2.timestamp(self.fim)
        ini = f'{int(ini)}000'
        fim = f'{int(fim)}000'
        response = requests.get(
            'https://hb.usa.skidata.com/maxxo/microsite/rest/b2c/reservation/productsearch',
            params={
                'start': ini,
                'end': fim,
                'promocode': promo,
            },
            headers={
                'lang': 'pt_BR',
                'tenantalias': 'RESB2CGRU',
            },
        )

        js = response.json()
        self.lista = sorted((min(j['price'],
                                 j['grossBestPrice']
                                 if j['grossBestPrice'] > 0
                                 else j['price']),
                             j['name'])
                            for j in js)
        aux = dict()
        for p, n in self.lista:
            if n not in self.lista:
                aux[n] = p
        self.lista = [(p, n.replace('Reserva', 'GRU'))
                      for n, p in aux.items()]


class EconoPark(Estacionamento):
    def __init__(self, ini: dt2, fim: dt2, promo: str):
        super().__init__(ini, fim)
        ini, fim = self.ini, self.fim
        response = requests.get('https://www.econoparkaeroporto.com.br/')
        cookies = response.cookies
        response = requests.get('https://www.econoparkaeroporto.com.br/Reservas.aspx',
                                cookies=cookies)
        token = get_hiddens(response.text)['_token']
        response = requests.post('https://www.econoparkaeroporto.com.br/Reservas.aspx',
                                 cookies=cookies,
                                 data={
                                     '_token': token,
                                     'initial-date': ini.strftime('%d/%m/%Y'),
                                     'initial-hour': ini.strftime('%H'),
                                     'initial-minute': ini.strftime('%M'),
                                     'final-date': fim.strftime('%d/%m/%Y'),
                                     'final-hour': fim.strftime('%H'),
                                     'final-minute': fim.strftime('%M'),
                                     'vehicle-qty': '1',
                                 })
        preco = re.search(r'Tarifa On-line</div>\s+R\$(\d+,\d{2})', response.text)
        assert preco, 'ERRO na busca do EconoPark!'
        self.lista = [(float(preco.group(1).replace(',', '.')),
                       '')]


class AeroPark(Estacionamento):
    """ https://www.aeroparking.com.br/index.php """

    def __init__(self, ini, fim, promo):
        super().__init__(ini, fim)
        nd = (self.fim - self.ini).days + int((self.fim - self.ini).seconds > 0)
        response = requests.get('https://www.aeroparking.com.br/precos/index.php')
        nums = re.findall(r'(\d+) [AÀ] (\d+) DIÁRIAS',
                          response.text,
                          flags=re.IGNORECASE)
        nums = list(map(lambda x: int(x[1]), nums))
        precos = re.findall(r'R\$\s*(\d+)\s*<span>\s*(,\d{2})', response.text)
        precos = list(map(lambda x: float(''.join(x).replace(',', '.')),
                          precos))
        # Descobertas
        nums_d = nums[:len(nums) // 2]
        precos_d = precos[:len(nums_d)]
        preco_d = None
        if nd <= nums_d[0]:
            preco_d = nd * precos_d[0]
        else:
            for ns, ps in zip(nums_d[1:], precos_d[1:]):
                if nd <= ns:
                    preco_d = ps
                    break
        nums_c = nums[len(nums_d):]
        precos_c = precos[len(nums_d):len(nums_d) + len(nums_c)]
        preco_c = None
        if nd <= nums_c[0]:
            preco_c = nd*precos_c[0]
        else:
            for ns, ps in zip(nums_c[1:], precos_c[1:]):
                if nd <= ns:
                    preco_c = ps
                    break

        if preco_d is not None:
            self.lista.append((preco_d, 'Descoberto'))
        if preco_c is not None:
            self.lista.append((preco_c, 'Coberto'))


class AirportPark(Estacionamento):
    """ https://airportpark.com.br/ """

    def __init__(self, ini, fim, promo):
        super().__init__(ini, fim)
        response = requests.get('https://airportpark.com.br/tarifa-reservas')
        ops = response.text.split('<select id="partnership"', 1)[1]
        ops = ops.split('</select', 1)[0]
        convenios = re.findall(r'<option value="\d+"\s*>([^<]+)', ops)
        convenios = ';'.join(convenios)
        cookies = response.cookies
        hid = get_hiddens(response.text)
        token = hid['_token']
        method = hid['_method']
        data = {
            '_token': token,
            '_method': method,
            'dataEntrada': self.ini.strftime('%d/%m/%Y'),
            'ddlHoraEntrada': self.ini.strftime('%H:%M'),
            'ddlQtdVeiculos': '1',
            'dataSaida': self.fim.strftime('%d/%m/%Y'),
            'ddlHoraSaida': self.fim.strftime('%H:%M'),
            'partnership': '',
            'partnershipTier': '',
            'coupon': promo,
        }

        response = requests.post('https://airportpark.com.br/tarifa-reservas', cookies=cookies,
                                 data=data)
        if 'não é válido' in response.text:
            data['coupon'] = ''
            response = requests.post('https://airportpark.com.br/tarifa-reservas', cookies=cookies,
                                     data=data)
        soup = BeautifulSoup(response.text,
                             "html.parser")
        div = soup.find("div",
                        {"class": 'price-amount'}
                        )
        span = div.find('span',
                        {'class': 'text-big'}
                        )
        preco = float(span.text.replace(',', '.'))
        self.lista = [(preco, '',
                       f'Convênios, verificar no site: {convenios}')]


class BRParking(Estacionamento):
    """ https://brparking.com.br/ """

    def __init__(self, ini, fim, promo):
        super().__init__(ini, fim)
        response = requests.get('https://brparking.com.br/')
        t1, p1 = re.search(r'<h2>até (\d+) horas</h2>\s*<span>R\$\s+([0-9,]+)</span>',
                           response.text,
                           flags=re.IGNORECASE).groups()
        t1 = int(t1)
        p1 = float(p1.replace(',', '.'))
        t2, p2 = re.search(r'<h2>Diária (24) HORAS</h2>\s*<span>R\$\s+([0-9,]+)</span>',
                           response.text,
                           flags=re.IGNORECASE).groups()
        t2 = int(t2)
        p2 = float(p2.replace(',', '.'))
        t3, t4, p34 = re.search(r'DE (\d+) À (\d+) DIAS</h2>\s*<span>R\$\s+([0-9,]+)</span>',
                                response.text,
                                flags=re.IGNORECASE).groups()
        t3 = int(t3)
        t4 = int(t4)
        p34 = float(p34.replace(',', '.'))
        t5, t6, p56 = re.search(r'Acima (\d+) À (\d+) DIAS</h2>\s*<span>R\$\s+([0-9,]+)</span>',
                                response.text,
                                flags=re.IGNORECASE).groups()
        t5 = int(t5)
        t6 = int(t6)
        p56 = float(p56.replace(',', '.'))
        ad1, ad2 = re.findall(r'Hora adicional R\$ ([0-9,]+)',
                              response.text,
                              flags=re.IGNORECASE)
        ad1 = float(ad1.replace(',', '.'))
        ad2 = float(ad2.replace(',', '.'))
        tol = int(re.search(r'Tolerância de até (\d+) horas',
                            response.text,
                            flags=re.IGNORECASE).group(1))
        if self.dt < timedelta(hours=t1):
            preco = p1
        elif self.dt < timedelta(days=t3):
            preco = p2 * self.dt.days + ad1 * math.ceil(self.dt.seconds / 3600)
        elif self.dt < timedelta(days=t4, hours=tol):
            preco = p34
        elif self.dt < timedelta(days=t6):
            preco = p56
        else:
            mais_30 = self.dt - timedelta(days=30)
            preco = p56 + ad2 * (mais_30.days * 24 + math.ceil(mais_30.seconds / 3600))
        self.lista = [(preco, '')]


class DecolarPark(Estacionamento):
    """ https://www.decolarpark.com.br/ """

    def __init__(self, ini, fim, promo):
        super().__init__(ini, fim)
        response = requests.get('https://www.decolarpark.com.br/')
        tabelas = re.split(r'tarifas - vagas (des)?cobertas',
                           response.text,
                           flags=re.IGNORECASE)[1:]
        for tabela, des in zip(tabelas[1::2], ['des', '']):
            for c1, c2 in re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*</tr>',
                                     tabela):
                t = re.search(r'(\d+) horas', c1)
                if not t:
                    continue
                t = int(t.group(1))
                p = float(re.search(r'R\$\s*(\d+,\d+)',
                                    c2).group(1).replace(',', '.'))
                if self.dt < timedelta(hours=t):
                    self.lista.append((p, f'{des}coberto'))
                    break


class FlyPark(Estacionamento):
    """ https://www.flypark.com.br/ """

    def __init__(self, ini, fim, promo):
        super().__init__(ini, fim)
        response = requests.get('https://flypark.com.br/')
        cookies = response.cookies
        params = {
            'date_start': self.ini.strftime('%d/%m/%Y'),
            'time_start': self.ini.strftime('%H:%M'),
            'date_end': self.fim.strftime('%d/%m/%Y'),
            'time_end': self.fim.strftime('%H:%M'),
        }
        response = requests.get('https://flypark.com.br/reservar',
                                params=params, cookies=cookies)
        soup = BeautifulSoup(response.text, 'html.parser')
        divs = soup.findAll('div',
                            {'class': 'reserve-product'})
        for div in divs:
            p = div.div.div.input['data-price'].replace(',', '.')
            tipo = div.findChildren('h3')[0].text
            tipo = re.sub(r'\s+', ' ', tipo).strip()
            self.lista.append((float(p), f'{tipo}'))


class PoncePark(Estacionamento):
    """ https://poncepark.com.br/ """

    def __init__(self, ini, fim, promo):
        super().__init__(ini, fim)
        ini = self.ini.strftime('%Y-%m-%dT%H:%M:00')
        fim = self.fim.strftime('%Y-%m-%dT%H:%M:00')
        for des in ['des', '']:
            response = requests.get(
                f'https://poncepark-app.movepark.com.br/api/v3/cart/calculation-price?product_slug=vaga-{des}coberta&'
                f'initial_date={ini}.000000Z&final_date={fim}.000000Z&lang=pt-br',
            )
            self.lista.append((response.json()['data']['cart']['total_price']['price_value'],
                               f'{des}coberto'))


class UniqueParking(Estacionamento):
    """ https://uniqueparking.com.br/ """

    def __init__(self, ini, fim, promo):
        super().__init__(ini, fim)
        response = requests.get('https://uniqueparking.com.br/')
        soup = BeautifulSoup(response.text, 'html.parser')
        sel = soup.find('select', {'name': 'input_15'})
        ops = [tuple(op['value'].split('|'))
               for op in sel.find_all('option')]
        for tipo, p in ops:
            p = float(p)
            p = p * self.dt.days + (p if self.dt.seconds > 3600 else 0)
            self.lista.append((p, f'{tipo}'))


class UrbanPark(Estacionamento):
    """ https://www.urbanparkgru.com.br/ """

    def __init__(self, ini, fim, promo):
        super().__init__(ini, fim)
        response = requests.get('https://www.urbanparkgru.com.br/',
                                headers={
                                    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
                                })
        soup = BeautifulSoup(response.text, 'html.parser')
        linhas = soup.find_all('th', {'scope': 'row'})
        ps = [linhas[0].parent.findChildren('td')[0].text,
              linhas[0].parent.findChildren('td')[1].text,
              linhas[-1].parent.findChildren('td')[0].text,
              linhas[-1].parent.findChildren('td')[1].text,
              ]
        ps = [0.01*int(re.sub(r'\D', '', pi))
              for pi in ps]
        t1, t2 = re.search(r'(\d+) a (\d+) dias',
                           linhas[-1].text).groups()
        t1 = int(t1)
        t2 = int(t2)
        if self.dt < timedelta(days=t1):
            preco1 = ps[0] * (self.dt.days + int(self.dt.seconds > 0))
            preco2 = ps[1] * (self.dt.days + int(self.dt.seconds > 0))
        elif self.dt < timedelta(days=t2):
            preco1 = ps[2]
            preco2 = ps[3]
        else:
            self.dt -= timedelta(days=t2)
            preco1 = ps[2] + ps[0] * (self.dt.days + int(self.dt.seconds > 0))
            preco2 = ps[3] + ps[1] * (self.dt.days + int(self.dt.seconds > 0))
        self.lista = [(preco1, 'descoberto'),
                      (preco2, 'coberto')]


