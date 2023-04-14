gnomAD release 2.1.1 contains a number of minor corrections, changes, and additions to the 2.1 data release. The major annotations, including allele count, allele number, and allele frequency, as well as variant filtering status, remain unchanged for the entire callset and for all subsets of the callset.

We corrected:
1. Filtering allele frequency (FAF) annotations: for any variant that occurs as a singleton in a population, the population-specific FAF should be 0. We have amended all FAF annotations accordingly.
2. VCF header formatting: we corrected histogram bin edges that were rounded incorrectly and annotations with the wrong Number encoding. We also added the overall background age distribution of release samples as a histogram annotation in the header.
3. The constraint files now correspond exactly to the filtering shown in the release files and browser (previously a small number of filtered variants were erroneously included). Additionally, they are now updated to the latest LOFTEE annotations (see below).

We changed:
1. Version 1.0 of LOFTEE is now used for variant annotation, which includes an improved END_TRUNC annotation and retires some filters. Predicted splice variants outside of the essential splice site are now given the OS (other splice) designation. Only HC variants are used to compute pLoF constraint metrics, including LOEUF.

We added:
1. Consanguineous allele frequencies: AFs for consanguineous individuals in certain subpopulations are now available in the 2.1.1 release Hail Table
2. A genome release VCF containing only variants in exome calling regions (by popular demand)

