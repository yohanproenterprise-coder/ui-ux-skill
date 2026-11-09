# Modèles d'IA inclus

## upscale-x4.onnx — agrandissement
Converti depuis Real-ESRGAN « realesr-general-x4v3 » et « realesr-general-wdn-x4v3 »
(mélange des poids 30 % / 70 %, méthode DNI prévue par les auteurs, pour un rendu naturel).
Source : https://github.com/xinntao/Real-ESRGAN — © 2021 Xintao Wang, licence BSD 3-Clause.

## lama.onnx — IA de retouche (téléchargé à la demande, non inclus)
LaMa (Carve / OpenCV Zoo), licence Apache 2.0 — https://github.com/advimman/lama

## Téléchargés à la demande (dossier .jarvis/models)
- real_esrgan_x2.onnx — Real-ESRGAN x2plus, © Xintao Wang, BSD 3-Clause (conversion ONNX : FaceFusion).
- yoloface_8n.onnx — détection des visages (YOLOv8 face, conversion FaceFusion).
- codeformer.onnx — CodeFormer, © S-Lab NTU, licence S-Lab 1.0 : usage personnel / non commercial uniquement.
- nomos8k_sc_x4.onnx — « Netteté renforcée » : 4xNomos8kSC de Philip Hofmann (Phhofm), licence CC BY 4.0
  (usage commercial autorisé en citant l'auteur), conversion ONNX : FaceFusion. Source : https://github.com/Phhofm/models
- gpen_bfr_256.onnx — GPEN (visages rapides), conversion FaceFusion ; voir la licence du dépôt d'origine
  (https://github.com/yangxy/GPEN) avant un usage commercial.

## Moteur carte graphique (facultatif, dossier .jarvis/gpu-runtime)
onnxruntime-directml (Microsoft, licence MIT), installé à la demande depuis les Réglages.
