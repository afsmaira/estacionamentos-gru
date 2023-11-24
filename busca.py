import sys

from estacionamentos import *

if __name__ == '__main__':
    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    cfg.read('config.cfg')
    dh1 = cfg['Estadia']['inicio']
    dh2 = cfg['Estadia']['fim']
    promos = cfg['Cupons']
    tds = len(sys.argv) > 1 and 'all' in sys.argv
    lst = []
    for k, v in cfg['Estacionamentos'].items():
        if tds or v == 'true':
            try:
                promo = promos.get('GRU', '')
                lst += eval(f'{k}("{dh1}", "{dh2}", "{promo}")')
            except (NameError, AttributeError, AssertionError) as err:
                print(err)
    print('\n' + '\n'.join(f'{n}: R$ {p:.2f} {c}'
                           for p, n, c in sorted(lst)))
