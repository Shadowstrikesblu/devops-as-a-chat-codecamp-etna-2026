# Modifications apportées au projet

> Journal des changements réalisés pour rendre la création d'infrastructure Terraform fonctionnelle de bout en bout (IA → génération Terraform → `plan`/`apply` AWS).
>
> Date : 2026-06-08

---

## Résumé

Trois blocages successifs ont été identifiés et corrigés lors d'une création d'instance EC2 via le chat :

1. **IA en mode mock** → la génération Terraform était impossible.
2. **Permissions AWS (IAM) insuffisantes** → `plan`/`apply` refusés par AWS.
3. **Bug de génération : AMI placeholder jamais résolue** → `apply` échouait sur `InvalidAMIID.Malformed`.

Seul le point 3 est une modification de **code**. Les points 1 et 2 sont des changements de **configuration** (fichier `.env` et IAM côté AWS).

---

## 1. Configuration IA — fichier `.env`

**Fichier :** [.env](.env)

**Problème :** la création Terraform renvoyait
`Mode IA mock actif: generation IA indisponible sans cle OpenAI`.
La clé `OPENAI_API_KEY` était renseignée, mais `DAC_AI_PROVIDER` était resté sur `mock`,
donc le client OpenAI n'était jamais instancié
(cf. [gpt_service.py:24](devops_api/app/services/gpt_service.py#L24)).

**Modification :**

```diff
- DAC_AI_PROVIDER=mock
+ DAC_AI_PROVIDER=openai
```

**Action associée :** redémarrage du backend pour recharger le `.env`
(`docker compose restart backend`), les variables étant lues au démarrage
([settings.py:9-10](devops_api/app/services/../settings.py)).

> ⚠️ Sécurité : la vraie clé OpenAI a transité en clair pendant le debug.
> Il est recommandé de la **révoquer/régénérer** sur
> https://platform.openai.com/api-keys et de vérifier que `.env` est bien dans `.gitignore`.

---

## 2. Permissions AWS (IAM) — côté console AWS (pas de fichier du repo)

**Problème :** Terraform `plan`/`apply` renvoyait des erreurs `403 UnauthorizedOperation`,
d'abord sur `ec2:DescribeVpcs`, puis sur `ec2:RunInstances`.
L'utilisateur IAM `harvey.mouloundou` n'avait pas de politique autorisant les actions EC2.

**Modification (hors repo, dans la console AWS) :**
attache de la policy **`AmazonEC2FullAccess`** à l'utilisateur IAM
(couvre `DescribeVpcs`, `RunInstances`, `CreateKeyPair`, `CreateSecurityGroup`,
`DescribeImages`, `CreateTags`, etc.).

> Note : ce n'est pas une modification du code, mais elle est indispensable
> pour que les déploiements fonctionnent. À documenter dans le guide étudiant
> comme prérequis AWS.

---

## 3. Correctif code — résolution de l'AMI placeholder

**Fichier modifié :** [devops_api/app/routes/generate_terraform.py](devops_api/app/routes/generate_terraform.py)

**Problème (root cause) :**
le prompt envoyé au LLM impose d'utiliser une AMI placeholder
`ami-xxxxxxxx` *« remplacée côté backend »*
([generate_terraform.py:1274](devops_api/app/routes/generate_terraform.py#L1274)),
**mais aucune étape de remplacement n'existait** dans ce flux de génération.
Le `main.tf` était donc écrit avec `ami = "ami-xxxxxxxx"`, ce qui faisait échouer
l'`apply` avec :

```
Error: creating EC2 Instance: operation error EC2: RunInstances,
api error InvalidAMIID.Malformed: Invalid id: "ami-xxxxxxxx" (expecting "ami-...")
```

Le resolver d'AMI existant ([ami_resolver.py](devops_api/app/services/ami_resolver.py))
n'était branché que sur un autre flux ([plan_executor.py:168](devops_api/app/services/plan_executor.py#L168)),
pas sur la route `generate_terraform`.

**Correctif :**
injection d'un data source Terraform `aws_ami` qui résout dynamiquement une AMI réelle
au moment du `plan`/`apply` (via `ec2:DescribeImages`), puis remplacement du placeholder
par une référence à ce data source. Avantages :
- pas besoin de credentials AWS au moment de la génération ;
- toujours une AMI **valide et à jour** pour la région courante
  (pas de mapping statique qui se périme) ;
- le choix de l'image suit l'OS détecté (`distro`).

Extrait ajouté (juste avant l'injection des outputs AWS) :

```python
# Résolution du placeholder AMI 'ami-xxxxxxxx' via un data source aws_ami.
if "ami-xxxxxxxx" in terraform_code:
    ami_lookup = {
        "ubuntu":       (["099720109477"], "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"),
        "debian":       (["136693071363"], "debian-12-amd64-*"),
        "amazon-linux": (["137112412989"], "amzn2-ami-hvm-*-x86_64-gp2"),
        "windows":      (["801119661308"], "Windows_Server-2022-English-Full-Base-*"),
    }
    owners, name_filter = ami_lookup.get(distro, ami_lookup["ubuntu"])
    # ... injecte data "aws_ami" "dac_default" { most_recent = true; owners; filter name/virtualization-type }
    terraform_code = terraform_code.replace('"ami-xxxxxxxx"', 'data.aws_ami.dac_default.id')
```

Le Terraform généré contient désormais :

```hcl
data "aws_ami" "dac_default" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "..." {
  ami = data.aws_ami.dac_default.id
  # ...
}
```

**Correctif de suivi (`name 'logger' is not defined`) :** une première version
du correctif ajoutait une ligne `logger.info(...)`, or aucun `logger` n'est défini
dans [generate_terraform.py](devops_api/app/routes/generate_terraform.py). Cette ligne
a été retirée (log non essentiel) pour éviter une `NameError` lors de la génération.

**Prise en compte du correctif :** le code source n'est **pas** monté en volume
(seul `dac_generated_files` l'est, cf. [docker-compose.yml:41-42](docker-compose.yml#L41-L42)),
donc l'image backend a dû être **reconstruite** :

```bash
docker compose up -d --build backend
```

---

## 4. Nettoyage d'état de session (opérationnel, base de données)

**Contexte :** après les correctifs, le chat renvoyait par intermittence
`Aucune étape détectée pour cette session` (message de
[generate_routes.py:212](devops_api/app/routes/generate_routes.py#L212)).

**Cause :** la session `s1` contenait des intents pollués créés pendant les tests :
- 4 intents au prompt vague `aws` (id 4-7) qui ne se parsent pas en spec VM
  (`_extract_create_specs` → `None`, cf. [plan_builder.py:131-133](devops_api/app/services/plan_builder.py#L131-L133)) ;
- des doublons `create aws`.

`build_plan` ne retient que les intents `pending`/`failed`
([plan_builder.py:105](devops_api/app/services/plan_builder.py#L105)). Comme une
génération réussie marque l'intent `generated` puis un échec d'apply le repassait
`pending`/`failed`, le plan oscillait entre « 1-2 steps » et « vide » → flapping.

**Action (non destructive, DB) :** ne conserver qu'**un seul** intent `create`
exploitable en `pending` (id 2), les autres passés à `generated` pour les exclure du plan :

```sql
UPDATE intents SET generation_status='generated'
  WHERE session_id=1 AND id IN (3,4,5,6,7);
UPDATE intents SET generation_status='pending'
  WHERE session_id=1 AND id=2;
```

Résultat : `build_plan(session_id=1)` → `status=success`, **1 step** (`compute_2.tf`).

> Piste d'amélioration produit (non faite) : rejeter / ne pas enregistrer les intents
> `create` dont le prompt ne produit aucune spec exploitable, pour éviter ce type de
> pollution silencieuse.

## 5. Correctif code — type d'instance Free Tier (`t2.micro` → `t3.micro`)

**Fichier modifié :** [devops_api/app/routes/generate_terraform.py](devops_api/app/routes/generate_terraform.py)

**Problème :** une fois l'AMI résolue et les permissions OK, l'`apply` échouait sur :

```
Error: creating EC2 Instance: RunInstances ...
api error InvalidParameterCombination: The specified instance type is not
eligible for Free Tier.
```

Le compte AWS est restreint au **Free Tier**, et `t2.micro` n'y est **pas éligible**
dans `eu-west-1` (c'est `t3.micro` qui l'est). Le type était codé en dur dans le
prompt de génération.

**Correctif :**
- prompt de génération : `instance_type: t2.micro` → `t3.micro` ;
- filet de sécurité post-génération (si le LLM ressort quand même `t2.micro`) :

```python
terraform_code = terraform_code.replace('"t2.micro"', '"t3.micro"')
```

**Déploiement :** rebuild de l'image backend (`docker compose up -d --build backend`).

## Vérifications effectuées

- ✅ IA active dans le conteneur après bascule `DAC_AI_PROVIDER=openai`.
- ✅ Reproduction de l'`apply` réel dans le workspace de l'app (`.exec_6`) :
  les credentials AWS et les permissions EC2 fonctionnent ; key_pair + security_group
  étaient créés, seule l'instance échouait à cause de l'AMI placeholder.
- ✅ Correctif présent dans l'image reconstruite (`data.aws_ami.dac_default`).
- ✅ Backend `healthy` après rebuild.

## Reste à faire / points d'attention

- [ ] **Régénérer** un Terraform via le chat puis relancer l'`apply` pour valider
      la création complète de l'instance EC2 de bout en bout.
- [ ] Ressources orphelines de l'apply partiel précédent (key_pair `generated-key-...`
      et security_group `allow-ssh-...`) : sans impact, mais peuvent être nettoyées
      côté AWS si besoin.
- [ ] (Optionnel) Améliorer la remontée d'erreur : l'app n'affiche que **stdout**
      de Terraform et tronque le message (~370 caractères), ce qui masquait la vraie
      erreur (présente dans **stderr**). Capturer aussi stderr faciliterait le debug.
- [ ] Révoquer/régénérer la clé OpenAI exposée pendant le debug.
