import json
import os
import sys
import tempfile
import unittest
from datetime import date

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(ICI))
import veille_boamp as vb  # noqa: E402

AUJOURD_HUI = date(2026, 9, 22)


def charger(nom):
    with open(os.path.join(ICI, nom), encoding="utf-8") as f:
        return json.load(f)


class TestFiltrage(unittest.TestCase):
    def setUp(self):
        self.config = charger("../config.json")
        self.resultats = vb.filtrer(charger("exemple_avis.json"), self.config, AUJOURD_HUI)
        self.ids = [r["idweb"] for r in self.resultats]

    def test_garde_les_bons_avis(self):
        self.assertEqual(set(self.ids), {"26-100001", "26-100002", "26-100008"})

    def test_exclusions(self):
        self.assertNotIn("26-100003", self.ids)  # mot exclu : voirie
        self.assertNotIn("26-100004", self.ids)  # hors zone
        self.assertNotIn("26-100005", self.ids)  # avis d'attribution
        self.assertNotIn("26-100006", self.ids)  # hors niche
        self.assertNotIn("26-100007", self.ids)  # date limite dépassée

    def test_classement(self):
        # 2 mots dans l'objet + zone + délai confortable arrive en tête
        self.assertEqual(self.ids[0], "26-100001")
        urgent = next(r for r in self.resultats if r["idweb"] == "26-100002")
        self.assertEqual(urgent["jours_restants"], 2)

    def test_accents_ignores(self):
        avis = {"objet": "PROPRETE DES GYMNASES", "nature_libelle": "Avis de marche",
                "code_departement": "75"}
        self.assertIsNotNone(vb.analyser(avis, self.config, AUJOURD_HUI))

    def test_zone_souple(self):
        config = {**self.config, "zone_stricte": False}
        ids = [r["idweb"] for r in vb.filtrer(charger("exemple_avis.json"), config, AUJOURD_HUI)]
        self.assertIn("26-100004", ids)
        # hors zone : classé après l'avis équivalent situé dans la zone
        self.assertLess(ids.index("26-100001"), ids.index("26-100004"))


class TestSorties(unittest.TestCase):
    def test_nouveaux_puis_deja_vus_et_fichiers(self):
        config = charger("../config.json")
        resultats = vb.filtrer(charger("exemple_avis.json"), config, AUJOURD_HUI)
        with tempfile.TemporaryDirectory() as tmp:
            vus = os.path.join(tmp, "vus.json")
            vb.marquer_nouveaux(resultats, vus)
            self.assertTrue(all(r["nouveau"] for r in resultats))
            vb.marquer_nouveaux(resultats, vus)
            self.assertFalse(any(r["nouveau"] for r in resultats))

            vb.ecrire_csv(resultats, os.path.join(tmp, "a.csv"))
            vb.ecrire_html(resultats, os.path.join(tmp, "r.html"), "Test <niche>")
            with open(os.path.join(tmp, "r.html"), encoding="utf-8") as f:
                page = f.read()
            self.assertIn("Test &lt;niche&gt;", page)
            self.assertIn("idweb:%2226-100001%22", page)


if __name__ == "__main__":
    unittest.main()
