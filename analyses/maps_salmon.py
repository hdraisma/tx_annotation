# For code to run, need to git clone onto gnomad_lof on cluster
import sys
sys.path.append('/home/hail/gnomad_lof')

from gnomad_hail import *
from gnomad_hail.resources.sample_qc import *
from gnomad_hail.utils.plotting import *
from constraint_utils import *
from tx_annotation import *

def load_tx_expression_data(tx_ht):
    tx_ht = tx_ht.rows()

    def process_expression_data(csq_expression):
        exprs_to_drop = ['ensg', 'csq', 'symbol', 'lof', 'lof_flag', 'mean_proportion']
        expression_data = csq_expression.drop(*exprs_to_drop)
        all_tissues = list(expression_data.values())
        expression_data_list = list(zip(list(expression_data), all_tissues))
        return csq_expression.select('ensg', 'csq', 'symbol', 'lof', 'lof_flag',
                                     Brain_Cortex=csq_expression.Brain_Cortex)

    return tx_ht.annotate(tx_annotation=tx_ht.tx_annotation.map(process_expression_data))

context_ht_path ="gs://gnomad-public/papers/2019-flagship-lof/v1.0/context/Homo_sapiens_assembly19.fasta.snps_only.vep_20181129.ht"
context_ht = hl.read_table(context_ht_path)

# Import and process gnomad 2.1.1 transcript annotation

base = "gs://gnomad-berylc/tx-annotation/hail2/reviewer_response/maximum_0/salmon_requantification_pc_only/"
#ht = hl.read_matrix_table("%sgnomad.exomes.r2.1.1.sites.salmon_pc_only.083119.ht"%base)
ht = hl.read_matrix_table("%sgnomad.exomes.r2.1.1.sites.salmon_pc_lncRNA.090119.ht"%base)


ht = ht.filter_rows(~hl.is_missing(ht.tx_annotation))
ht = ht.annotate_rows(tx_annotation = ht.tx_annotation.map(fix_loftee_beta_nonlofs))
ht = load_tx_expression_data(ht)
ht = hl.MatrixTable.from_rows_table(ht)
ht = pull_out_worst_from_tx_annotate(ht)

# Only consider variants that pass RF
ht = ht.rows()
ht = ht.filter(hl.len(ht.filters) == 0)
context = context_ht[ht.key]
ht = ht.annotate(context=context.context, methylation=context.methylation)
ht = prepare_ht(ht, trimer=True, annotate_coverage=False)

# Prepare MAPS data
even_breaks = [0.999, 0.995, 0.99, 0.98] + list(map(lambda x: x/40, range(39, -1, -1)))

ht = ht.filter(ht.freq[0].AN > 125748 * 0.8 * 2)
mutation_ht = hl.read_table(mutation_rate_ht_path)


# Only consider LOFTEE HC pLoFs, missense and synonymous
ht = ht.annotate(keep = hl.case(missing_false=True)
                 .when((ht.csq == "stop_gained") &(ht.lof == 'HC'), "keep")
                 .when((ht.csq == "splice_donor_variant") &(ht.lof == 'HC'), "keep")
                 .when((ht.csq == "splice_acceptor_variant" ) &(ht.lof == 'HC'), "keep")
                 .when(ht.csq == "missense_variant", "keep")
                 .when(ht.csq == "synonymous_variant", "keep").default('filter'))


ht = ht.filter(ht.keep == "keep")

# Group pLoFs, remember can't calculate MAPs on frameshifts (no mutational model)
ht = ht.annotate(worst_csq = hl.case(missing_false=True)
                 .when(ht.csq == "stop_gained", "pLoF")
                 .when(ht.csq == "splice_donor_variant", "pLoF")
                 .when(ht.csq == "splice_acceptor_variant", "pLoF")
                 .when(ht.csq == "missense_variant", "missense_variant")
                 .when(ht.csq == "synonymous_variant", "synonymous_variant").default('irrev_var'),
                 lof = ht.lof)

print("finished processing")

def add_rank(ht, field, ascending=True, total_genes=None, bins=10, defined_only=False):
    if total_genes is None:
        if defined_only:
            total_genes = ht.aggregate(hl.agg.count_where(hl.is_defined(ht[field])))
        else:
            total_genes = ht.count()
    rank_field = ht[field] if ascending else -ht[field]
    ht = ht.key_by(_rank=rank_field).add_index(f'{field}_rank').key_by()
    ht = ht.annotate(**{f'{field}_rank': hl.or_missing(
        hl.is_defined(ht._rank), ht[f'{field}_rank']
    )}).drop('_rank')
    return ht.annotate(**{
        f'{field}_bin': hl.int(ht[f'{field}_rank'] * bins / total_genes),
        f'{field}_bin_6': hl.int(ht[f'{field}_rank'] * 6 / total_genes)
    })

constraint = hl.read_table(constraint_ht_path)
constraint = add_rank(constraint, 'oe_lof_upper', defined_only=True)
constraint = constraint.rename({"gene": "symbol"})
constraint = constraint.key_by("symbol")
ht = ht.key_by("symbol")

ht_constraint = ht.annotate(constraint_bin = constraint[ht.symbol].oe_lof_upper_bin,
                            constraint_value = constraint[ht.symbol].oe_lof_upper)
ht_constraint.show()
def run_maps_constraint_binexport(f, write, mut_ht = mutation_ht):
    m = maps(f, mut_ht, ['constraint_bin'])
    m.export(write)

oe_constraint_bin_below_01 = ht_constraint.filter(ht_constraint.Brain_Cortex < 0.1)
oe_constraint_bin_below_01.show()
run_maps_constraint_binexport(oe_constraint_bin_below_01,
                             "gs://gnomad-berylc/tx-annotation/hail2/reviewer_response/maximum_0/salmon_requantification_pc_only/maps_salmon/maps.pc_lncrna.low.expression.083119.tsv.bgz")


print('wrote low')

oe_constraint_bin_above_09 = ht_constraint.filter(ht_constraint.Brain_Cortex > 0.9)
oe_constraint_bin_above_09.show()
run_maps_constraint_binexport(oe_constraint_bin_above_09,
                              "gs://gnomad-berylc/tx-annotation/hail2/reviewer_response/maximum_0/salmon_requantification_pc_only/maps_salmon/maps.pc_lncrna.high.expression.083119.tsv.bgz")
print('wrote high')

oe_constraint_bin_between =  ht_constraint.filter((ht_constraint.Brain_Cortex <= 0.9) & (ht_constraint.Brain_Cortex >= 0.1))
run_maps_constraint_binexport(oe_constraint_bin_between,
                              "gs://gnomad-berylc/tx-annotation/hail2/reviewer_response/maximum_0/salmon_requantification_pc_only/maps_salmonmaps.pc_lncrna.medium.expression.083119.tsv.bgz")
print('done')