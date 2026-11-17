# Radicle: topologija čvorova, repoa i ljudi

Ovaj dokument objašnjava kako je [Radicle](https://radicle.dev) organiziran.
Polazi od fizičkih računala, preko git repoa na njima, do ljudi koji svojim
ključevima potpisuju promjene. Cilj je da se odnosi među entitetima vide kao
mapa u 2D prostoru. Uz to je skica kako bi se `catholicit` preslikao na taj
model. Napisano u studenom 2026., za Radicle 1.10.x (protokol *Heartwood*).

Sadržaj:

1. [Sažetak](#1-sažetak)
2. [Rječnik entiteta](#2-rječnik-entiteta)
3. [Svijet: fizički čvorovi i gossip mreža](#3-svijet-fizički-čvorovi-i-gossip-mreža)
4. [Ljudi, ključevi, uređaji, čvorovi](#4-ljudi-ključevi-uređaji-čvorovi)
5. [Unutar jednog čvora: storage i repoi](#5-unutar-jednog-čvora-storage-i-repoi)
6. [Unutar jednog repoa: prostori imena i refovi](#6-unutar-jednog-repoa-prostori-imena-i-refovi)
7. [Model entiteta (ER)](#7-model-entiteta-er)
8. [Tok: od commita do kanonskog `main`a](#8-tok-od-commita-do-kanonskog-maina)
9. [Tok: patch od nedelegata](#9-tok-patch-od-nedelegata)
10. [Isti repo, različit pogled sa svakog čvora](#10-isti-repo-različit-pogled-sa-svakog-čvora)
11. [Primjer: `catholicit` na Radicleu](#11-primjer-catholicit-na-radicleu)
12. [Što ni Radicle ne decentralizira](#12-što-ni-radicle-ne-decentralizira)
13. [Tim kroz vrijeme: dolasci i odlasci](#13-tim-kroz-vrijeme-dolasci-i-odlasci)
14. [Disk i otkrivanje: usporedba s blockchain čvorom](#14-disk-i-otkrivanje-usporedba-s-blockchain-čvorom)
15. [Codeberg i Radicle](#15-codeberg-i-radicle)
16. [Izvori i što još treba provjeriti](#16-izvori-i-što-još-treba-provjeriti)

---

## 1. Sažetak

- **Nema servera, računa ni blockchaina.** Svako računalo s pokrenutim
  `radicle-node` je ravnopravan čvor (peer). Čvorovi gossip protokolom
  razmjenjuju samo *najave* (tko sam, koje repoe imam, koji su mi refovi
  novi). Sam git sadržaj dohvaćaju izravno jedan od drugoga.
- **Identitet je kriptografski ključ.** Osoba generira Ed25519 ključ
  (`rad auth`). Javni ključ je istovremeno njezin **DID** (`did:key:z6Mk…`) i
  **NID**, odnosno identitet njezinog čvora.
- **Repo ima svoj identitet (RID)** i potpisani **identitetski dokument**.
  U njemu su ime, zadana grana, popis **delegata** (DID-ova) i **prag**
  (threshold).
- **Unutar repoa svaki sudionik ima vlastiti prostor imena** (namespace).
  Tamo su njegove grane i potpisani popis refova (`sigrefs`). Nitko ne može
  pisati u tuđi prostor jer bi potpis pao.
- **„Službena” grana** (kanonski `refs/heads/main`) nije zapisana na nekom
  serveru. Svaki čvor je **sam izračuna**: to je commit na kojem se slaže
  barem *prag* delegata.
- **Issues i patchevi** (COB, *collaborative objects*) su potpisani zapisi
  operacija unutar istog git repoa. Repliciraju se zajedno s kodom.

---

## 2. Rječnik entiteta

| Entitet | Što je fizički | Identifikator | Primjer |
|---|---|---|---|
| **Osoba** | Čovjek | nema, Radicle ne zna za „osobu” | Matija |
| **Ključ / DID** | Ed25519 par ključeva u `~/.radicle/keys/` | `did:key:z6Mk…` | ključ na Mac miniju |
| **Uređaj** | Računalo na kojem ključ živi | nema, samo hostname | Mac mini, laptop |
| **Čvor (node)** | Proces `radicle-node` na uređaju | **NID** = javni ključ | `z6MkfX…@1.2.3.4:8776` |
| **Seed** | Čvor koji je stalno upaljen, ima javnu adresu i replicira tuđe repoe | NID + adresa | Oracle VPS, `iris.radicle…` |
| **Storage** | Direktorij `~/.radicle/storage/` s *bare* git repoima | putanja | |
| **Repo** | Jedan *bare* git repo u storageu | **RID** `rad:z3gq…` | `governance` |
| **Identitetski dokument** | Potpisani JSON u `refs/rad/id` | hash revizije | delegati + prag |
| **Delegat** | DID naveden u identitetskom dokumentu | DID | 2 Ownera |
| **Prostor imena** | `refs/namespaces/<NID>/…` unutar repoa | NID | Matijina kopija grana |
| **Sigrefs** | Potpisani popis svih refova jednog sudionika | `refs/namespaces/<NID>/refs/rad/sigrefs` | |
| **COB** | Issue, patch ili identitet kao lanac git commitova s operacijama | `refs/cobs/<tip>/<id>` | `xyz.radicle.patch` |
| **Kanonski ref** | `refs/heads/main` izračunat iz glasova delegata | | |
| **Radna kopija** | Običan `git clone` s remoteom `rad` | | `~/git/catholicit/governance` |

Najvažnija razlika prema GitHubu: **„osoba” i „uređaj” ne postoje u
protokolu.** Postoje samo ključevi. Ako jedna osoba ima dva uređaja s dva
ključa, za Radicle su to dva sudionika. Zato se oba ključa navode kao
delegati, ili se isti ključ prenese na oba uređaja.

---

## 3. Svijet: fizički čvorovi i gossip mreža

Svaki pravokutnik je stvarno računalo negdje u svijetu. Pune linije su
trajne veze između čvorova (gossip). Isprekidane linije su veze koje se
uspostave samo kad laptop ili mobitel izađe online. Mreža **nema središte**.
Bootstrap seedovi samo pomažu novom čvoru da nađe prve susjede.

```mermaid
flowchart TB
    subgraph EU_Zagreb["Zagreb, ured"]
        MINI["Mac mini<br/>čvor z6MkMATI…<br/>stalno upaljen, iza NAT-a"]
    end
    subgraph EU_Frankfurt["Frankfurt, Oracle Cloud"]
        ORA["OCI VPS / Coolify<br/>SEED z6MkORA…<br/>javna IP, port 8776<br/>+ radicle-httpd za web"]
    end
    subgraph EU_Other["Drugdje u EU"]
        HET["Član B: VPS<br/>SEED z6MkBBB…"]
        LAP["Član C: laptop<br/>čvor z6MkCCC…<br/>online povremeno"]
    end
    subgraph Global["Javna Radicle mreža"]
        IRIS["Bootstrap seed 1<br/>Radicle tim"]
        ROSA["Bootstrap seed 2<br/>Radicle tim"]
        X1["tisuće drugih čvorova<br/>koji repliciraju<br/>svoje repoe"]
    end

    MINI === ORA
    MINI === IRIS
    ORA === HET
    ORA === IRIS
    HET === ROSA
    IRIS === ROSA
    ROSA === X1
    IRIS === X1
    LAP -.-> ORA
    LAP -.-> HET

    WEB["Preglednik bilo koga<br/>app.radicle.network ili<br/>vlastiti web na ORA"] -->|HTTP, samo čitanje| ORA
```

Što se šalje po linijama:

| Poruka | Sadržaj | Kad |
|---|---|---|
| **Node announcement** | „Ja sam NID X, dostupan na adresi Y” | pri spajanju, periodički |
| **Inventory announcement** | „Repliciram RID-ove A, B, C” | kad počnem ili prestanem pratiti repo |
| **Refs announcement** | „U repou A moji su refovi sada na hashu H” | nakon `git push rad` |
| **Git fetch** | Stvarni git objekti, *izravno* od čvora koji ih ima | kad primim najavu za repo koji pratim |

Svaki čvor iz inventory najava gradi vlastitu **tablicu usmjeravanja**: za
svaki RID zna koji ga čvorovi imaju. Ne postoji globalni registar repoa.

---

## 4. Ljudi, ključevi, uređaji, čvorovi

Lijevo su stvarni ljudi, u sredini kriptografski identiteti, desno procesi
na računalima. Strelice pokazuju „posjeduje / pokreće”. Desni stupac
pokazuje kako identitet ulazi u repo.

```mermaid
flowchart LR
    subgraph Ljudi["Stvarni ljudi"]
        P1["Matija"]
        P2["Drugi Owner"]
        P3["Vanjski suradnik"]
    end

    subgraph Kljucevi["Ključevi = DID = NID"]
        K1["did:key:z6MkMATI…<br/>Mac mini"]
        K1b["did:key:z6MkMATL…<br/>laptop"]
        K2["did:key:z6MkOWN2…"]
        K3["did:key:z6MkVANJ…"]
        KS["did:key:z6MkORA…<br/>ključ seeda,<br/>nije ničija osoba"]
    end

    subgraph Cvorovi["Procesi radicle-node"]
        N1["čvor na Mac miniju"]
        N1b["čvor na laptopu"]
        N2["čvor drugog Ownera"]
        N3["čvor suradnika"]
        NS["seed na Oracleu"]
    end

    subgraph Repo["Repo rad:z3GOV… governance"]
        ID["Identitetski dokument<br/>delegati: MATI, MATL, OWN2<br/>prag: 2"]
        NS1["namespace MATI"]
        NS1b["namespace MATL"]
        NS2["namespace OWN2"]
        NS3["namespace VANJ"]
    end

    P1 --> K1 --> N1
    P1 --> K1b --> N1b
    P2 --> K2 --> N2
    P3 --> K3 --> N3
    KS --> NS

    K1 -. delegat .-> ID
    K1b -. delegat .-> ID
    K2 -. delegat .-> ID
    K1 -- piše --> NS1
    K1b -- piše --> NS1b
    K2 -- piše --> NS2
    K3 -- piše --> NS3
```

Napomene:

- **Seed ima vlastiti ključ, ali ne mora biti delegat.** On samo replicira i
  poslužuje. Nema nikakvu vlast nad repoom. Ako Oracle ugasi VPS, gubi se
  jedna kopija, nikakvo pravo.
- **Vanjski suradnik ima svoj namespace** u istom repou čim objavi patch, ali
  nije delegat. Njegove grane se vide, ali ne utječu na kanonski `main`.
- **Prag 2 od 3 ključa** u primjeru je malo varljiv: dva od tri ključa
  pripadaju Matiji, pa bi on sam mogao ispuniti prag. U pravoj postavi
  osoba treba imati **jedan delegatski ključ**, ili prag treba računati s
  tim (vidi [§11](#11-primjer-catholicit-na-radicleu)).

---

## 5. Unutar jednog čvora: storage i repoi

Jedan čvor drži mnogo repoa. Koje će repoe replicirati odlučuje **seeding
policy** tog čvora. Vlasnik čvora sam odlučuje što hostira. Nitko mu ne
može narediti da nešto čuva ili obriše.

```mermaid
flowchart TB
    subgraph Uredjaj["Fizičko računalo: Oracle VPS"]
        subgraph Proc["Procesi"]
            NODE["radicle-node<br/>port 8776<br/>gossip + git fetch"]
            HTTPD["radicle-httpd<br/>HTTP API za web,<br/>samo čitanje"]
        end
        subgraph Home["~/.radicle/"]
            KEYS["keys/radicle<br/>keys/radicle.pub"]
            CFG["config.json<br/>seeding policy:<br/>allow governance, org-app<br/>block sve ostalo"]
            DB["node/ — SQLite<br/>tablica usmjeravanja,<br/>adrese čvorova, policy"]
            subgraph Storage["storage/"]
                R1["z3GOV…/<br/>bare git repo<br/>governance"]
                R2["z4APP…/<br/>bare git repo<br/>org-app"]
                R3["z2XYZ…/<br/>tuđi repo koji<br/>ovaj seed prati"]
            end
        end
    end

    NODE --> KEYS
    NODE --> CFG
    NODE --> DB
    NODE <--> Storage
    HTTPD --> Storage
    NET(("Radicle mreža")) <--> NODE
    BROWSER["web preglednik"] --> HTTPD
```

A ovako izgleda isto na računalu developera, gdje postoji i **radna kopija**:

```mermaid
flowchart LR
    subgraph Mac["Mac mini"]
        WC["Radna kopija<br/>~/git/catholicit/governance<br/>.git s remoteom 'rad'"]
        HELPER["git-remote-rad<br/>helper"]
        ST["~/.radicle/storage/z3GOV…<br/>bare repo"]
        NODE["radicle-node"]
    end
    WC -- "git push rad main" --> HELPER
    HELPER -- "piše u moj namespace<br/>i potpisuje sigrefs" --> ST
    HELPER -- "javi čvoru" --> NODE
    NODE -- "refs announcement" --> NET(("mreža"))
    NET -- "git fetch tuđih namespacea" --> NODE --> ST
    ST -- "git pull rad / rad sync" --> WC
```

Ključni detalj: `git push rad` **ne ide na mrežu, nego u lokalni storage**.
Mreža tek nakon toga dozna da postoji nešto novo i sama to povuče. Zato
Radicle radi i offline: commitaš, pushaš, otvaraš issue, a sve se
sinkronizira kad se spojiš.

---

## 6. Unutar jednog repoa: prostori imena i refovi

Ovo je stvarna struktura refova u jednom *bare* repou u storageu. Svaki
sudionik ima podstablo `refs/namespaces/<NID>/`. Git objekti (commitovi,
stabla, blobovi) dijele se, a refovi su odvojeni.

```mermaid
flowchart TB
    REPO["storage/z3GOV…/<br/>(bare git repo)"]

    REPO --> CAN["refs/heads/main<br/>KANONSKI: commit oko kojeg se<br/>slaže ≥ prag delegata"]
    REPO --> RADID["refs/rad/id<br/>identitetski dokument<br/>(delegati, prag, ime, vidljivost)"]
    REPO --> COBS["refs/cobs/"]
    REPO --> NSS["refs/namespaces/"]

    COBS --> ISS["xyz.radicle.issue/&lt;id&gt;<br/>lanac commitova s operacijama:<br/>otvori, komentiraj, oznaka, zatvori"]
    COBS --> PAT["xyz.radicle.patch/&lt;id&gt;<br/>revizije, review, merge"]
    COBS --> IDC["xyz.radicle.id/&lt;id&gt;<br/>prijedlozi izmjene identiteta"]

    NSS --> M["z6MkMATI…/ (delegat)"]
    NSS --> O["z6MkOWN2…/ (delegat)"]
    NSS --> V["z6MkVANJ…/ (suradnik)"]

    M --> M1["refs/heads/main → a1b2c3"]
    M --> M2["refs/heads/feature-x"]
    M --> M3["refs/rad/sigrefs<br/>potpis MATI nad svim gornjim refovima"]
    O --> O1["refs/heads/main → a1b2c3"]
    O --> O3["refs/rad/sigrefs<br/>potpis OWN2"]
    V --> V1["refs/heads/patch/fix-typo"]
    V --> V3["refs/rad/sigrefs<br/>potpis VANJ"]

    M1 -. "glas za a1b2c3" .-> CAN
    O1 -. "glas za a1b2c3" .-> CAN
```

Kako se izračuna kanonski `main`: delegati MATI i OWN2 imaju svoj `main`
na istom commitu `a1b2c3`. Prag je 2, pa je kanonski `main` = `a1b2c3`.
Suradnikove grane ne broje se jer on nije delegat.

**Dvije razine potpisa:**

| Što se potpisuje | Čime | Što dokazuje |
|---|---|---|
| `sigrefs` | uvijek, automatski, Radicle ključem | „Ovi refovi u mom namespaceu su moji, nitko ih nije podmetnuo” |
| sam commit | opcionalno, git SSH potpisom istim ključem | „Ja sam autor ovog commita” |

Sigrefs štiti **objavu**: tko je rekao da je grana tu. Potpis commita štiti
**autorstvo**. Za organizaciju je razumno tražiti oboje.

---

## 7. Model entiteta (ER)

```mermaid
erDiagram
    OSOBA ||--o{ KLJUC : "posjeduje"
    KLJUC ||--|| CVOR : "je identitet (NID)"
    UREDJAJ ||--o{ CVOR : "pokreće"
    CVOR ||--|| STORAGE : "ima"
    STORAGE ||--o{ REPO : "sadrži kopije"
    CVOR }o--o{ CVOR : "gossip veza"
    REPO ||--|| IDENTITETSKI_DOKUMENT : "refs/rad/id"
    IDENTITETSKI_DOKUMENT ||--|{ DELEGAT : "navodi"
    DELEGAT }o--|| KLJUC : "je"
    REPO ||--o{ NAMESPACE : "sadrži"
    NAMESPACE }o--|| KLJUC : "pripada"
    NAMESPACE ||--|| SIGREFS : "potpisan s"
    NAMESPACE ||--o{ GRANA : "sadrži"
    REPO ||--o{ COB : "sadrži"
    COB }o--o{ KLJUC : "operacije potpisuju"
    REPO ||--|| KANONSKI_REF : "izračunava se"
    KANONSKI_REF }o--|{ DELEGAT : "prag glasova"
```

Kako čitati važne veze:

- **Repo nije na jednom mjestu.** `STORAGE ||--o{ REPO` znači da svaki čvor
  koji prati repo ima *svoju punu kopiju*. Isti RID postoji na N računala.
- **`KLJUC ||--|| CVOR`** znači: jedan ključ, jedan identitet čvora. Osoba
  može imati više ključeva (`OSOBA ||--o{ KLJUC`).
- **`KANONSKI_REF`** nije pohranjen kao autoritet nego se izračunava. Dva
  čvora s istim podacima uvijek izračunaju isti rezultat.

---

## 8. Tok: od commita do kanonskog `main`a

```mermaid
sequenceDiagram
    autonumber
    actor M as Matija (delegat)
    participant WC as Radna kopija (Mac mini)
    participant SM as Storage + čvor (Mac mini)
    participant SO as Seed (Oracle)
    participant SB as Čvor drugog Ownera
    actor O as Drugi Owner (delegat)

    M->>WC: git commit -S (SSH potpis)
    M->>WC: git push rad main
    WC->>SM: upiši u refs/namespaces/MATI/refs/heads/main<br/>+ novi sigrefs potpis
    SM-->>SO: refs announcement (z3GOV, MATI, hash)
    SO->>SM: git fetch (MATI namespace)
    SO->>SO: provjeri sigrefs potpis
    SO-->>SB: refs announcement (prosljeđuje)
    SB->>SO: git fetch
    Note over SO,SB: Kanonski main još NIJE pomaknut:<br/>samo 1 od 2 delegata je na novom commitu
    O->>SB: rad sync, pregleda, git merge --ff-only
    O->>SB: git push rad main
    SB-->>SO: refs announcement (OWN2, isti hash)
    SO->>SB: git fetch
    Note over SM,SB: Sada se 2 od 2 delegata slažu.<br/>Svaki čvor SAM izračuna novi kanonski main.
```

Usporedba s GitHubom: na GitHubu „merge” znači da server promijeni jedan
ref. Ovdje „merge” znači da **dovoljno delegata u svojim potpisanim
namespaceima pokaže na isti commit**. To je multisig nad Gitom.

---

## 9. Tok: patch od nedelegata

```mermaid
sequenceDiagram
    autonumber
    actor V as Vanjski suradnik
    participant NV as Njegov čvor
    participant SO as Seed (Oracle)
    participant NM as Čvor Matije
    actor M as Matija (delegat)

    V->>NV: rad clone rad:z3GOV…
    Note over V,NV: Klon dolazi s bilo kojeg čvora<br/>koji ima repo, ne s "originala"
    V->>NV: commit + git push rad HEAD:refs/patches
    NV->>NV: novi COB xyz.radicle.patch/<id><br/>+ grana u namespaceu VANJ
    NV-->>SO: refs announcement
    SO->>NV: fetch
    SO-->>NM: announcement
    NM->>SO: fetch
    M->>NM: rad patch show / rad patch checkout
    M->>NM: rad patch review --accept (operacija u COB-u)
    M->>NM: git merge + git push rad main
    NM->>NM: patch automatski označen kao merged<br/>(commit je ušao u delegatov main)
    NM-->>SO: announcement
    SO-->>NV: announcement
    Note over V,NM: Suradnik nikad nije trebao račun,<br/>dozvolu ni pristup ikakvom serveru.
```

---

## 10. Isti repo, različit pogled sa svakog čvora

Radicle je **eventualno konzistentan**. U danom trenutku čvorovi mogu imati
različit podskup namespacea. Kanonski `main` se svugdje izračuna istim
pravilom, pa se slože čim imaju iste podatke.

```mermaid
flowchart LR
    subgraph A["Mac mini vidi"]
        A1["MATI: main → c3"]
        A2["OWN2: main → b2"]
        A3["kanonski: b2<br/>(c3 ima samo 1 glas)"]
    end
    subgraph B["Oracle seed vidi"]
        B1["MATI: main → c3"]
        B2["OWN2: main → c3"]
        B3["kanonski: c3"]
    end
    subgraph C["Laptop člana C<br/>(bio offline tjedan dana)"]
        C1["MATI: main → a1"]
        C2["OWN2: main → a1"]
        C3["kanonski: a1"]
    end
    B -- "Mac mini dohvati OWN2" --> A
    B -- "laptop se spoji" --> C
```

Nakon sinkronizacije sva tri čvora izračunaju `c3`. Nema glasanja *mreže* i
nema „najdužeg lanca”. Svaki repo ima svoje delegate i svoj prag, i to je
cijeli „konsenzus”. Zato blockchain nije potreban.

---

## 11. Primjer: `catholicit` na Radicleu

Kako bi se postojeći model (Safe multisig + GitHub + Peribolos) preslikao na
Radicle:

```mermaid
flowchart TB
    subgraph Odluke["Izvor legitimiteta"]
        SAFE["Safe multisig<br/>owneri + prag"]
    end

    subgraph Rad["Radicle"]
        GOV["rad:… governance<br/>delegati = isti ljudi kao Safe owneri<br/>prag = većina"]
        APP["rad:… org-app"]
        OTHER["rad:… ostali repoi"]
    end

    subgraph Seedovi["Fizički seedovi, svaki na drugoj infrastrukturi"]
        S1["Oracle VPS (Coolify)"]
        S2["Mac mini, ured"]
        S3["VPS člana B"]
        S4["javni Radicle seedovi"]
    end

    subgraph Ogledala["Samo za vidljivost, nisu izvor istine"]
        GH["GitHub catholicit/*"]
        CB["Codeberg"]
    end

    SAFE -- "promjena članstva =<br/>izmjena identitetskog dokumenta<br/>(rad id update, prag potpisa)" --> GOV
    GOV --- S1 & S2 & S3 & S4
    APP --- S1 & S2
    OTHER --- S1 & S3
    S1 -- "jednosmjerni mirror<br/>kanonskog main" --> GH
    S1 -- mirror --> CB
```

Pravila koja iz toga slijede:

1. **Jedan delegatski ključ po osobi.** Isti ljudi kao Safe owneri, svatko
   svoj ključ generira sam. Dodatni uređaji sinkroniziraju radne kopije, ali
   ne dobivaju delegatski ključ, da prag ostane stvarni broj ljudi.
2. **Prag = većina delegata**, isto pravilo kao glasanje u `governance.yml`.
3. **Izmjena članstva je izmjena identitetskog dokumenta**, koju također
   moraju potpisati delegati do praga. Odluka u Safeu i izmjena u Radicleu
   trebaju se poklapati (isti uzorak kao „GitHub == Safe?” u
   [arhitektura.md](arhitektura.md)).
4. **Barem tri seeda na tri različite infrastrukture**, da ni Oracle, ni ured,
   ni ijedan član ne budu nužni.
5. **GitHub postaje ogledalo**: push ide samo s Radiclea prema GitHubu, nikad
   obrnuto.
6. **Za sada samo javni repoi.** Vidi [§12](#12-što-ni-radicle-ne-decentralizira).

---

## 12. Što ni Radicle ne decentralizira

| Ovisnost | Zašto postoji | Ublažavanje |
|---|---|---|
| **Bootstrap seedovi** Radicle tima | Novi čvor mora znati bar jednu adresu | U config dodati vlastite seedove; tada tim nije nužan |
| **Javna IP / NAT** | Čvor iza routera ne prima dolazne veze | Bar jedan seed s javnom adresom (Oracle), Tor ili I2P adrese (podržano od 1.9) |
| **DNS za web prikaz** | `app.radicle.network` i vlastiti httpd rade preko domene | Web je samo prikaz; protokol radi i bez njega |
| **Privatni repoi** | Objavljena je ranjivost: čvorovi šalju privatne repoe nešifrirano | Za sada samo javni repoi; čekati Radicle 2.0 (QUIC + TLS) |
| **Prelazak na 2.0** | Čvorovi 1.x i 2.x se neće moći međusobno spojiti | Planirati jednu koordiniranu nadogradnju svih seedova |
| **CI** | Protokol ga nema | Radicle CI broker ili Forgejo Actions runner koji prati Radicle |
| **Gubitak ključa** | Nema „zaboravljene lozinke” | Prag < broj delegata, pa ostali delegati mogu izmijeniti identitet i zamijeniti izgubljeni ključ |
| **Platforme** | Linux, macOS, BSD; Windows ne | |

---

## 13. Tim kroz vrijeme: dolasci i odlasci

Radicle **nema pojam organizacije ni tima**, samo repoe s delegatima. Postoji
jedna javna Radicle mreža (radicle.network je domena projekta, ne zasebna
mreža). „Naša mreža” je samo podgraf: čvorovi koji seedaju RID-ove iz našeg
registra.

**Developer ne treba dozvolu da bi doprinosio.** Svatko s ključem može
klonirati repo i objaviti patch u svoj namespace. Popis treba voditi samo za
one koji smiju mergeati (delegate).

| Uloga | Koliko | U Radicleu |
|---|---|---|
| Suradnik | cijeli tim + bilo tko izvana | ništa osim `rad auth` |
| Delegat (maintainer) | 3–5 po repou | DID u identitetskom dokumentu |
| Prag | npr. 2/3 ili 3/5 | broj u identitetskom dokumentu |

Ne raditi 11 delegata s pragom 6. Prag vrijedi i za merge i za izmjenu
identiteta, pa bi svaki merge tražio šest ljudi.

| Događaj | Radnja | Tko potpisuje |
|---|---|---|
| novi suradnici | samo `org.yaml` (evidencija) + follow na seedovima | nitko |
| novi maintainer | `rad id update --delegate did:key:…` u svakom repou | prag postojećih delegata (`rad id accept`) |
| maintainer ode / izgubi ključ | `rad id update` bez njegovog DID-a | prag ostalih, bez njega |
| povijest odlazećeg | ostaje valjana, samo više ne glasa | |

```mermaid
flowchart TB
    SAFE["Glasanje (Safe / governance PR)"] --> ORG["org.yaml: članovi,<br/>delegati po repou, registar RID-ova"]
    ORG --> SYNC["rad-sync skripta na seedovima (cron)"]
    SYNC --> POL["seeding policy: allow za RID-ove iz registra"]
    SYNC --> FOL["follow svih članova"]
    SYNC --> DIFF{"delegati u org.yaml ==<br/>delegati u identitetu repoa?"}
    DIFF -- da --> OK["ništa"]
    DIFF -- ne --> PROP["otvori prijedlog revizije identiteta<br/>(rad id update) u svakom repou"]
    PROP --> SIGN["delegati svojim ključem: rad id accept"]
    SIGN --> PRAG{"prag dostignut?"}
    PRAG -- da --> NEW["nova revizija vrijedi na svim čvorovima"]
    PRAG -- ne --> SIGN
```

Bot **ne smije** potpisivati umjesto delegata, jer bi tada bot bio vlast
(ista granica kao kod Safea). Automatizira se sve osim potpisa.

Seedovi za javni open source: scope `all` za RID-ove iz registra (da patchevi
vanjskih suradnika stignu bez dogovora), `block` za spam čvorove, barem tri
seeda na tri infrastrukture.

---

## 14. Disk i otkrivanje: usporedba s blockchain čvorom

Radicle **nema globalnog stanja**. Čvor čuva samo repoe koje sam seeda. Za
usporedbu, Gnosis arhivski čvor (Nethermind, godinu dana povijesti) treba
~250 GB jer čuva stanje cijele mreže.

| Dio na disku seeda | Veličina |
|---|---|
| naši repoi (RID-ovi iz registra) | koliko su veliki |
| forkovi suradnika (namespacei u istom repou) | mali, git dijeli objekte |
| issues, patchevi (COB) | zanemarivo |
| tablica usmjeravanja (SQLite: RID → čvorovi, adrese) | reda MB, raste s brojem čvorova i repoa, ne s njihovom veličinom |
| tuđi repoi | 0, osim ako ih eksplicitno seedamo |

Otkrivanje: bootstrap seedovi → node announcements (adrese) → inventory
announcements (tko ima koji RID, samo popis) → `rad clone` povuče sadržaj
izravno od čvora koji ga ima. **Nema globalne pretrage**, pa RID treba
objaviti u README-u ogledala na GitHubu ili Codebergu i na webu.

Procjena: 20 repoa (jedan 2 GB, ostali ~50 MB) s desetcima suradnika je
~3–4 GB po seedu. Dovoljni su Mac mini ili Oracle Free Tier.

| Rizik | Kontrola |
|---|---|
| spam od 10 GB u nečijem namespaceu uz scope `all` | ograničenje veličine fetcha u configu, `block` NID, ili scope `followed` |
| binarne datoteke u gitu | ne držati ih u gitu; službenog Git LFS-a nema |
| napušteni forkovi | čišćenje namespacea koji nisu delegati ni praćeni |
| seed koji slučajno seeda sve | default policy `block`, `allow` samo iz registra |

---

## 15. Codeberg i Radicle

Codeberg je **centralni hosting u vlasništvu zajednice** (Codeberg e.V.,
Berlin, Forgejo). Radicle je **protokol bez vlasnika**.

| | Codeberg | Radicle |
|---|---|---|
| model | jedna hostana instanca | P2P, kod na svakom čvoru koji ga seeda |
| identitet | račun (e-mail, lozinka, 2FA) | Ed25519 ključ (`did:key`) |
| tko te može izbaciti | udruga, po pravilima korištenja (npr. neslobodna licenca) | nitko; pojedini seed može odbiti repo |
| pravo merganja | dozvole u bazi servera | delegati + prag u potpisanom dokumentu |
| upravljanje | skupština članova udruge | svaki repo sam |
| issues / PR | u bazi servera | COB-ovi u repou, rade offline |
| CI, Pages | Forgejo Actions / Woodpecker, Codeberg Pages | nema ugrađeno |
| otkrivanje | pretraga, explore | slabo |
| točka kvara | jedna institucija, jurisdikcija, datacentar | bootstrap seedovi (zaobilazivo), DNS za web |
| suverenost | institucionalna (vjeruješ udruzi) | kriptografska (vjeruješ ključevima) |

Vlastiti Forgejo na Coolifyju je treća varijanta: suverenost operatera, uz
ovisnost o Oracleu kao infrastrukturi.

Uloge za `catholicit`: **Radicle** je izvor istine za kod i merge, **Safe**
za članstvo i odluke, **Codeberg i GitHub** su ogledala za vidljivost, a CI
ide na vlastiti runner.

---

## 16. Izvori i što još treba provjeriti

- [radicle.dev](https://radicle.dev/), glavna stranica od 23.04.2026.
  (prije radicle.xyz)
- [Radicle Protocol Guide](https://radicle.dev/guides/protocol)
- [Radicle 1.9.0](https://radicle.dev/2026/05/19/radicle-1.9.0) (I2P, Tor)
- [docs.radicle.xyz](https://docs.radicle.xyz)
- [Ranjivost: privatni repoi nešifrirano](https://maninak.com/blog/radicle-cleartext-transport-vulnerability/)
- [Arch Wiki: Radicle](https://wiki.archlinux.org/title/Radicle)

Ovaj dokument je napisan prema Protocol Guideu i općem poznavanju
Heartwooda, bez lokalno instaliranog `rad`. Nakon `rad init` na Mac miniju
treba provjeriti i po potrebi ispraviti:

- točne nazive refova: `git -C ~/.radicle/storage/<RID> for-each-ref`
- oblik identitetskog dokumenta: `rad inspect --identity`
- da su DID i NID isti ključ: `rad self`
- trenutne bootstrap seedove i njihove domene: `rad config`
- canonical reference rules (prag po grani) u 1.10.x
- točan naziv opcije za ograničenje veličine fetcha i naredbu za čišćenje
  namespacea; default seeding policy
- stvarna potrošnja diska i veličina baze nakon seedanja jednog javnog repoa
