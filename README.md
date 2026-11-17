# catholicit/governance

> Detaljna dokumentacija s dijagramima: [`docs/arhitektura.md`](docs/arhitektura.md)

Organizacija **github.com/catholicit** upravlja se glasanjem, a ne preko
administratora. Ovaj repo je njen ustav i njen jedini administrator.

- **Svi članovi su ravnopravni.** Svi su u timu `core` s pravom **Admin** na sve
  repoe (osim ovog, koji se mijenja samo glasanjem).
- **Nitko nije iznad drugih.** Owner organizacije je bot (GitHub App
  `catholicit-governance`), koji radi isključivo ono što piše u `members.yml`
  na grani `main`.
- **`main` mijenja samo bot**, i to tek kad prijedlog dobije većinu.

## Kako se pridružiti

Otvori pull request koji te dodaje u [`members.yml`](members.yml):

```yaml
  - github: tvoj-username
    evm:            # neobavezno: adresa walleta, za glasanje Safe potpisima
```

Kad prijedlog prođe, bot ti pošalje pozivnicu u organizaciju. Prihvati je na
<https://github.com/orgs/catholicit/invitation>.

## Kako se glasa

1. Prijedlog je pull request na `main`, iz forka (nitko osim bota nema pravo
   pisanja u ovaj repo).
2. Članovi glasaju recenzijom: **Approve** je ZA, **Request changes** je PROTIV.
   Vrijede samo glasovi na zadnjem commitu. Novi commit poništava sve glasove.
3. Autor prijedloga, ako je član, računa se kao ZA.
4. Prijedlog prolazi kad ima **više od polovice članova ZA** (`floor(n/2) + 1`)
   i otvoren je barem **24 sata**. Ako su ZA svi članovi, prolazi odmah.
5. Bot broji glasove kod svake promjene PR-a, svakih 15 minuta i na komentar
   `/prebroji`. Rezultat i popis promjena u organizaciji piše u komentar na PR-u.
6. Kad prijedlog prođe, bot ga spoji, a `apply` workflow uskladi organizaciju.

Pravila glasanja (`quorum:` u `members.yml`) i sam kod bota (`scripts/`,
`.github/workflows/`) mijenjaju se istim postupkom.

## Što bot radi

| Workflow | Kada | Što |
|---|---|---|
| `quorum` | PR, `/prebroji`, svakih 15 min | broji glasove, spaja prihvaćene prijedloge |
| `apply` | merge na `main`, svaki dan | poziva i uklanja članove, tim `core`, prava na repoe, postavke organizacije; ispravlja ručne promjene |
| `backup` | svaki dan | mirror svih repoa na Codeberg (kad su postavljeni `CODEBERG_TOKEN` i `CODEBERG_ORG`) |

Bot nikad ne dodjeljuje ulogu Owner. Ownera koji nije naveden pod `owners:`
spusti u običnog člana.

## Gdje je povjerenje (iskreno)

- **Privatni ključ GitHub Appa** i pristup bot računu koji je Owner. Tko ih ima,
  može zaobići glasanje. Plan: ključ i recovery kodove podijeliti Shamirovom
  shemom među više članova (npr. 3-od-5), tako da ih nitko nema sam.
- **GitHub** može zaključati organizaciju. Zato postoji `backup`.
- **Prijelazno stanje:** dok je `stepanic` naveden pod `owners:`, on tehnički može
  sve. Faza 2 ga uklanja.

## Faze

1. ✅ Governance repo, glasanje PR recenzijama, bot uskladi organizaciju.
2. ⏳ Bot račun `catholicit-bot` postaje jedini Owner, ljudi se spuštaju u
   članove, ključ se dijeli Shamirom. Mirror na Codeberg/Radicle.
3. ⏳ Glasanje Safe multisig potpisima (svaki član ima `evm` adresu); `quorum`
   provjerava on-chain potpise umjesto PR recenzija.

## Postavljanje (jednom)

1. GitHub App iz [`app/manifest.json`](app/manifest.json), instaliran na
   organizaciju na **sve repoe**.
2. Na ovom repou: varijabla `GOVERNANCE_APP_ID` i secret
   `GOVERNANCE_APP_PRIVATE_KEY`.
3. Ruleset na `main`: zabranjeno brisanje, force push i svaka izmjena, osim za App.
