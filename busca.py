import sys

from estacionamentos import *

if __name__ == '__main__':
    na = len(sys.argv)
    assert na >= 5
    d1, h1, d2, h2 = sys.argv[1:5]
    # TODO: list of promo codes
    promo = sys.argv[5] if na > 5 else ''
    dh1 = d1+' '+h1
    dh2 = d2+' '+h2
    lst = list(GRU(dh1, dh2, promo))
    lst += EconoPark(dh1, dh2)
    lst += AeroPark(dh1, dh2)
    print('\n'.join(f'{n}: R$ {p:.2f}'
                    for p, n in sorted(lst)))

