# estacionamentos-gru

Busca e lista por ordem de prerço alguns estacionamentos próximos ao aeroporto de guarulhos

## Estacionamentos

Segue a lista de estacionamentos atualmente suportados:

- GRU
- AeroPark
- AirportPark
- BRParking
- DecolarPark
- EconoPark
- FlyPark
- PoncePark
- UniqueParking
- UrbanPark
- ViajePark

## Configuração

O arquivo de configuração (`config.cfg`) deve seguir o modelo abaixo:

```ini
[Estacionamentos]
;true -> adiciona o estacionamento à busca
;false -> remove o estacionamento da busca
;Essa seção é ignorada se for passado o parâmetro all para o programa
GRU = false
AeroPark = false
AirportPark = false
BRParking = false
DecolarPark = false
EconoPark = false
FlyPark = false
PoncePark = false
UniqueParking = false
UrbanPark = false
ViajePark = false

[Estadia]
;Informações da estadia
inicio = 2023-10-05 15:00
fim = 2023-10-08 15:00

[Cupons]
;Cupom a ser usado para cada um dos estacionamentos
GRU = 5PDA

[Maps]
;Se esses dados forem preenchidos,
;será calculada a distâcia do estacionamento
;ao terminal escolhido (padrão 1)
APIKey = AIza...
terminal = 2
```
