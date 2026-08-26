# Reference corrections for progress so far v3.md — byte-verified 2026-08-22
Source of truth: arXiv API (export.arxiv.org/api/query?id_list=...) and Crossref (api.crossref.org/works). Every line below was fetched in session cd70aff0; nothing is from memory.

## A. The Rahman block (8 entries, manuscript lines ~483-574). Four have the wrong first author.
| # | As written | Verified record | Action |
|---|---|---|---|
| 1 | Rahman, M. R., et al. (2019). Share, but be aware... ICSME | Rahman, M. R., Rahman, A., & Williams, L. (2019). *Share, but be aware: Security smells in Python gists.* ICSME 2019. doi:10.1109/ICSME.2019.00087 | list all three authors; add DOI |
| 2 | Rahman, M. R., et al. (2021). Security smells in Ansible and Chef scripts: A replication study. TOSEM | **Rahman, A.**, Rahman, M. R., Parnin, C., & Williams, L. (2021). TOSEM. doi:10.1145/3408897; arXiv:1907.07159 | **FIRST AUTHOR WRONG** (Akond Rahman) |
| 3 | Rahman, M. R., et al. (2022). Why secret detection tools are not enough... EMSE | Rahman, M. R., Imtiaz, N., Storey, M.-A., & Williams, L. (2022). *Empirical Software Engineering.* doi:10.1007/s10664-021-10109-y | list authors; add DOI |
| 4 | Rahman, M. R., et al. (2025a). Unveiling malicious logic... arXiv preprint | **Ryan, A.**, Ifti, J. M., Erfan, M., Rahman, A. A. U., & Rahman, M. R. (2025). arXiv:2512.12559 | **FIRST AUTHOR WRONG** (M. R. Rahman is 5th of 5); add arXiv ID |
| 5 | Rahman, M. R., et al. (2025b). FALCON... arXiv preprint | **Mitra, S.**, Neupane, S., Duclos, M., Mittal, S., Piplai, A., Rahman, M. R., Zieglar, E., & Rahimi, S. (2025). arXiv:2508.18684 | **FIRST AUTHOR WRONG** (M. R. Rahman is 6th of 8); add arXiv ID |
| 6 | Rahman, M. R., et al. (2025c). If you cannot measure it... JISA | Rahman, M. R., Rahman, I., & Williams, L. (2025). *Journal of Information Security and Applications.* doi:10.1016/j.jisa.2025.104056 (SSRN 2024 preprint doi:10.2139/ssrn.5004048) | list authors; add DOI |
| 7 | Rahman, M. R., et al. (2026a). From natural language to verified code... Dafny | **Erfan, M.**, Chowdhury, M. K. H., Ryan, A., & Rahman, M. R. (2026). arXiv:2604.22601 | **FIRST AUTHOR WRONG** (M. R. Rahman is 4th of 4); add arXiv ID |
| 8 | Rahman, M. R., et al. (2026b). Mind the gap: Evaluating LLMs for high-level malicious package detection vs. fine-grained indicator identification. arXiv preprint | **UNRESOLVED** — arXiv title searches on three distinct fragments return nothing; see addendum for Crossref | either locate the primary record or remove the citation; the manuscript's own footnote already concedes this block was scraped from a Scholar page |

## B. Antigravity's six "MISMATCH" flags are NOT errors
Dettmers 2022 (ICLR 2022 vs arXiv 2021), D'Amour 2022 (JMLR 2022 vs arXiv 2020), Kingma & Ba 2015 (ICLR 2015 vs arXiv 2014), McCoy 2020 (BlackboxNLP 2020 vs arXiv 2019), Marx 2020 (ICML 2020 vs arXiv 2019), Zhuang 2022 (MLSys 2022 vs arXiv 2021): the manuscript cites the venue year, which is correct practice. No change.

## C. Antigravity's three "suggested identifiers" are wrong — do not use
doi:10.1109/trustcom53373.2021.00091 (a different 2021 paper), doi:10.55041/ijsrem61574, doi:10.1109/icassp40776.2020.9052960 (an ICASSP 2020 DOI offered for a 2026 paper). They were Crossref's top fuzzy hits, not matches.

## D. New citations the memo and refuter require (titles/authors fetched by Antigravity; 4 of 14 independently re-fetched here and all four matched)
- Nikolich, A., Kiselev, I., Platonov, V., & Romanova, K. (2026). *Weight-Space Geometry of Offline Reasoning Training.* arXiv:2606.23740. [re-fetched: title, authors, and the §3.4 quote "different weights, same basin" all confirmed]
- Jang, U., Lee, J. D., & Ryu, E. K. (2024). LoRA training in the NTK regime has no spurious local minima. arXiv:2402.11867.
- Zhu, J., Greenewald, K., Nadjahi, K., Sáez de Ocáriz Borde, H., Brüel Gabrielsson, R., Choshen, L., Ghassemi, M., Yurochkin, M., & Solomon, J. (2024). Asymmetry in low-rank adapters of foundation models. ICML 2024; arXiv:2402.16842. [already in v3]
- Zhang, L., Zhang, L., Shi, S., Chu, X., & Li, B. (2023). LoRA-FA. arXiv:2308.03303.
- Yu, X., Wang, Y., Chen, J., & Xue, L. (2025). AltLoRA. arXiv:2505.12455.
- Bui, N., Savova, G., & Wang, L. (2025). Assessing the macro and micro effects of random seeds on fine-tuning large language models. arXiv:2503.07329. [re-fetched ✓]
- Hamman, F., Dissanayake, P., Mishra, S., Lecue, F., & Dutta, S. (2024). Quantifying prediction consistency under fine-tuning multiplicity in tabular LLMs. arXiv:2407.04173. [re-fetched ✓]
- Hazan, H., Zhang, Y., Hartl, B., & Levin, M. (2026). A little rank goes a long way: Random scaffolds with LoRA adapters are all you need. arXiv:2604.08749. [re-fetched ✓]
- Shuttleworth, R., Andreas, J., Torralba, A., & Sharma, P. (2024). LoRA vs full fine-tuning: An illusion of equivalence. arXiv:2410.21228.
- Wang, Y., Lin, Y., Zeng, X., & Zhang, G. (2023). MultiLoRA. arXiv:2311.11501.
- Paul, R. (2026). Spectral geometry of LoRA adapters encodes training objective and predicts harmful compliance. arXiv:2604.08844. [re-fetched ✓]
- Qin, Y., et al. (2022). Exploring mode connectivity for pre-trained language models. arXiv:2210.14102.
- Altintas, G. S., Bachmann, G., Noci, L., & Hofmann, T. (2023). Disentangling linear mode-connectivity. arXiv:2312.09832.
- Schulman, J., & Thinking Machines Lab (2025). LoRA without regret. https://thinkingmachines.ai/blog/lora/
Still to resolve before use (cited in the memo, not yet fetched): Li, Chen & Zhu 2309.01507; Topollai & Choromanska 2603.16731; Subramanian 2607.08733; 2603.17771; 2502.01235; 2602.08239; 2412.05418; 2602.22600; 2608.00860; 2508.11985; 2605.03724; 2603.12228; 2607.11022; Malladi kernel view; Woodworth 2020; Chizat 1812.07956.

## Addendum — entry 8 ("Mind the gap", Rahman 2026b)
Crossref query.title returns three unrelated papers (MalLoc 2025; LEGF-DST 2025; Nguyen et al. 2026). arXiv returns nothing on "Mind the Gap: Evaluating LLMs for High-Level Malicious Package Detection", "Fine-Grained Indicator Identification", or au:Rahman AND "Malicious Package Detection". Status: **UNRESOLVED after 4 independent queries** — no primary record located. Recommendation: remove from the reference list (and the one body mention) unless the author can supply the record.
