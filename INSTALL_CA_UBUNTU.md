# Installer le certificat local sur Ubuntu

Cette procédure permet à Ubuntu de faire confiance au certificat HTTPS local d’Inventory, notamment pour utiliser la caméra et le micro depuis le navigateur.

## Télécharger et installer le certificat

Depuis l’ordinateur Ubuntu qui accède à Inventory, ouvre un terminal et exécute :

```bash
wget http://ADRESSE_IP_DU_PC:18767/ca.crt -O inventory-local-ca.crt
sudo install -m 0644 inventory-local-ca.crt /usr/local/share/ca-certificates/inventory-local-ca.crt
sudo update-ca-certificates
```

Si l’adresse IP du PC hébergeant Inventory change, remplace `ADRESSE_IP_DU_PC` par sa nouvelle adresse.

Ferme puis rouvre le navigateur, et ouvre :

```text
https://ADRESSE_IP_DU_PC:18766
```

## Si le navigateur affiche encore un avertissement

Certains navigateurs utilisent leur propre magasin de certificats. Les navigateurs installés en Snap, par exemple, peuvent ne pas reprendre automatiquement le magasin de confiance système. Dans ce cas, importe `inventory-local-ca.crt` dans les autorités de certification de confiance du navigateur, puis redémarre-le.

## Si Ubuntu héberge aussi Inventory

Le certificat est déjà présent sur cette machine. Tu peux installer directement le fichier local :

```bash
sudo install -m 0644 "$HOME/.inventory/tls/ca.crt" /usr/local/share/ca-certificates/inventory-local-ca.crt
sudo update-ca-certificates
```

Le fichier `ca.crt` est le certificat public à installer. Ne partage pas `~/.inventory/tls/ca.key`, qui est la clé privée de l’autorité locale.

## Importer le certificat directement dans Chrome

Si Chrome affiche encore une erreur de certificat après l’installation Ubuntu ci-dessus, importe aussi l’autorité dans Chrome :

1. Télécharge le certificat depuis `http://ADRESSE_IP_DU_PC:18767/ca.crt` si tu ne l’as pas déjà.
2. Dans Chrome, ouvre `chrome://settings/certificates`.
3. Clique sur **Gérer les certificats**, puis ouvre l’onglet **Autorités**.
4. Clique sur **Importer** et sélectionne `inventory-local-ca.crt`.
5. Si Chrome propose des options de confiance, autorise ce certificat à identifier des sites Web.
6. Ferme puis rouvre Chrome, puis va sur `https://ADRESSE_IP_DU_PC:18766`.

Chromium documente cette page comme l’interface de gestion des certificats sous Linux. Selon la version de Chrome et le magasin de certificats utilisé, le certificat système Ubuntu peut ne pas apparaître automatiquement dans Chrome. [Documentation Chromium sur les certificats Linux](https://chromium.googlesource.com/chromium/src/+/master/docs/linux/cert_management.md)
