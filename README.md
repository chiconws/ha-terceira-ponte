# ha-terceira-ponte

Integração Terceira Ponte para Home Assistant.

Integração customizada para Home Assistant que expõe as quatro câmeras públicas da Terceira Ponte, em Vitória/ES, como entidades `camera`.

As imagens são obtidas do serviço da CETURB-ES com autenticação JWT pública e cache curto para reduzir requisições duplicadas quando o dashboard é aberto.

## Recursos

- 4 entidades `camera` fixas:
  - `Subida Vitória`
  - `Descida Vitória`
  - `Subida Vila Velha`
  - `Descida Vila Velha`
- Configuração por UI em `Configurações > Dispositivos e Serviços`
- Cache configurável nas opções da integração
- Renovação automática do token JWT
- Compatível com HACS

## Instalação

### HACS

1. Adicione este repositório como repositório customizado no HACS.
2. Selecione a categoria `Integration`.
3. Instale a integração `Terceira Ponte`.
4. Reinicie o Home Assistant.

### Manual

1. Copie a pasta `custom_components/ha_terceira_ponte` para `custom_components`.
2. Reinicie o Home Assistant.

## Configuração

1. Vá em `Configurações > Dispositivos e Serviços`.
2. Adicione a integração `Terceira Ponte`.
3. Confirme a configuração.
4. Se quiser ajustar o cache, abra `Configurar` nas opções da integração.

## Limitações conhecidas

- O feed é snapshot JPEG, não stream de vídeo.
- A disponibilidade depende do serviço público da CETURB-ES.
- O backend observado em 12 de março de 2026 exige JWT público e muda as imagens em intervalos curtos, mas sem contrato público documentado de atualização.

