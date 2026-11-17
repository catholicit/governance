# catholicit/governance

> Detaljna dokumentacija s dijagramima: [`docs/arhitektura.md`](docs/arhitektura.md)

Organizacija **github.com/catholicit** upravlja se glasanjem, a ne preko
administratora. Ovaj repo je njen ustav i njen jedini administrator.

- **Svi članovi su ravnopravni.** Svi su u timu `core` s pravom **Admin** na sve
  repoe (osim ovog, koji se mijenja samo glasanjem).
- **Stanje organizacije je [`org.yaml`](org.yaml)** u formatu alata
  [Peribolos](https://docs.prow.k8s.io/docs/components/cli-tools/peribolos/),
  istog koji koriste Kubernetes, Knative i Istio. Pravila glasanja su u
  [`governance.yml`](governance.yml).
- **Primjenu radi bot** (GitHub App `catholicit-governance`), isključivo prema
  onome što piše na grani `main`.
- **`main` mijenja samo bot**, i to tek kad prijedlog dobije većinu.

## Kako se pridružiti

Otvori pull request koji te dodaje u [`org.yaml`](org.yaml), pod `members:`
organizacije i pod `members:` tima `core`. Neobavezno, u
[`governance.yml`](governance.yml) pod `evm:` dodaj adresu walleta za buduće
glasanje Safe potpisima.

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

Pravila glasanja (`governance.yml`) i sam kod bota (`scripts/`,
`.github/workflows/`) mijenjaju se istim postupkom.

## Što bot radi

| Workflow | Kada | Što |
|---|---|---|
| `quorum` | PR, `/prebroji`, svakih 15 min | broji glasove, u komentar stavi Peribolos dry-run, spaja prihvaćene prijedloge |
| `apply` | merge na `main`, svaki dan | Peribolos: Owneri, članovi, tim `core`, prava na repoe, postavke organizacije; ispravlja ručne promjene |
| `backup` | svaki dan | mirror svih repoa na Codeberg (kad su postavljeni `CODEBERG_TOKEN` i `CODEBERG_ORG`) |

## Gdje je povjerenje (iskreno)

- **Dva Ownera** (`admins:` u `org.yaml`; Peribolos ne dopušta manje od 2).
  Tehnički mogu sve, ali svaki njihov potez je javan, a `apply` svaki dan
  vraća organizaciju na izglasano stanje.
- **Privatni ključ GitHub Appa.** Tko ga ima, može zaobići glasanje.
- **GitHub** može zaključati organizaciju. Zato postoji `backup`.

## Faze

1. ✅ Governance repo, glasanje PR recenzijama, Peribolos uskladi organizaciju.
2. ⏳ Mirror na Codeberg i Radicle (pravo na fork).
3. ⏳ Glasanje Safe multisig potpisima (svaki član ima `evm` adresu u
   `governance.yml`); `quorum` provjerava potpise umjesto PR recenzija.
4. ⏳ Eksperiment: zaključani root Owneri, uz izlaz u nuždi preko glasanja.

## Postavljanje (jednom)

1. GitHub App iz [`app/manifest.json`](app/manifest.json), instaliran na
   organizaciju na **sve repoe**.
2. Na ovom repou: varijabla `GOVERNANCE_APP_ID` i secret
   `GOVERNANCE_APP_PRIVATE_KEY`.
3. Ruleset na `main`: zabranjeno brisanje, force push i svaka izmjena, osim za App.
