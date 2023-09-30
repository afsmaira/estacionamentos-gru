""" https://www.melhoresdestinos.com.br/estacionamento-aeroporto-guarulhos.html """
import re
import requests
from datetime import datetime as dt2


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
            return r
        raise StopIteration


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
    def __init__(self, ini: dt2, fim: dt2):
        super().__init__(ini, fim)
        ini, fim = self.ini, self.fim
        response = requests.post('https://www.econoparkaeroporto.com.br/Reservas.aspx',
                                 cookies={
                                     'econopark_aeroporto_session': 'eyJpdiI6IlNHcWhSMnJwXC90Tkg5SHR3a3JmdFdBPT0iLCJ2YWx1ZSI6ImNiRlM5d1hUYjlvVGw0SVBzZGdnZElxTzU4cWxEQjVXaFwvNEhMNnZPSFZaUFFpcVQwZFJYOWM2TTZRK0VqVjdOV0c3eWxsOTZuVnFVVjBJV0lZXC9kRnkwSUhlVGJnUVJKaUVEOXpEVk9XUStcL0tQZzJ0ODJ6bU1ybEZJZGtKSVhzIiwibWFjIjoiNTlkZTkwNTQ4MGUyZDA3MWQyNWU5MDM2YmYwYjZmYzE5ZGE4YmIxOTQ4NmY0YzcyZTNlNTY3ZmE1ZmE2ZGM4OSJ9'
                                 },
                                 data={
                                     '_token': 'gNlC7y5f33FH39ehyrcqmc43FVYeB8zsDqtj3NJv',
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
                       'EconoPark')]


class AeroPark(Estacionamento):
    def __init__(self, ini, fim):
        super().__init__(ini, fim)
        nd = (self.fim-self.ini).days + int((self.fim-self.ini).seconds > 0)
        response = requests.get('https://www.aeroparking.com.br/precos/index.php')
        nums = re.findall(r'(\d+) [AÀ] (\d+) DIÁRIAS',
                          response.text,
                          flags=re.IGNORECASE)
        nums = list(map(lambda x: int(x[1]), nums))
        precos = re.findall(r'R\$\s*(\d+)\s*<span>\s*(,\d{2})', response.text)
        precos = list(map(lambda x: float(''.join(x).replace(',', '.')),
                          precos))
        # Descobertas
        nums_d = nums[:len(nums)//2]
        precos_d = precos[:len(nums_d)]
        preco_d = None
        if nd <= nums_d[0]:
            preco_d = nd*precos_d[0]
        else:
            for ns, ps in zip(nums_d[1:], precos_d[1:]):
                if nd <= ns:
                    preco_d = ps
                    break
        nums_c = nums[len(nums_d):]
        precos_c = precos[len(nums_d):len(nums_d)+len(nums_c)]
        preco_c = None
        if nd <= nums_c[0]:
            preco_c = nd*precos_c[0]
        else:
            for ns, ps in zip(nums_c[1:], precos_c[1:]):
                if nd <= ns:
                    preco_c = ps
                    break

        if preco_d is not None:
            self.lista.append((preco_d, 'AeroPark descoberto'))
        if preco_c is not None:
            self.lista.append((preco_c, 'AeroPark coberto'))


