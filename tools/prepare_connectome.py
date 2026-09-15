"""Convert Winding et al. supplementary CSVs into a compact runtime pack."""
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd
from scipy import sparse

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('source',type=Path); ap.add_argument('--out',type=Path,default=Path('data/connectome')); args=ap.parse_args()
    matrix=args.source/'all-all_connectivity_matrix.csv'; annotations=args.source/'annotations.csv'
    print('Reading 2,952 x 2,952 synapse-count matrix…')
    frame=pd.read_csv(matrix,index_col=0)
    ids=np.asarray(frame.index.astype(str)); values=frame.to_numpy(dtype=np.float32)
    # Rows are presynaptic and columns postsynaptic; store postsynaptic x presynaptic.
    weights=sparse.csr_matrix(values.T); del values, frame
    incoming=np.asarray(weights.sum(axis=1)).ravel(); weights=sparse.diags(1/np.maximum(incoming,40))@weights
    ann=pd.read_csv(annotations,dtype=str).fillna(''); lookup={v:i for i,v in enumerate(ids)}
    groups={}
    rules={'olfactory':'olfactory','visual':'visual','thermo_warm':'thermo-warm','thermo_cold':'thermo-cold','mechano':'mechano','proprio':'proprio','noci':'noci'}
    for name,needle in rules.items():
        rows=ann[ann.additional_annotations.str.contains(needle,case=False,regex=False)]
        found=[]
        for col in ('left_id','right_id'):
            found += [lookup[x] for x in rows[col] if x in lookup]
        groups[name]=sorted(set(found))
    rows=ann[ann.celltype.str.fullmatch('DN-VNC',case=False)]
    groups['dn_vnc']=sorted(set(lookup[x] for c in ('left_id','right_id') for x in rows[c] if x in lookup))
    neurons=[{'index':i,'id':str(neuron_id),'side':'','celltype':'','annotations':'','cluster':''} for i,neuron_id in enumerate(ids)]
    for _,row in ann.iterrows():
        for column,side in (('left_id','left'),('right_id','right')):
            neuron_id=row[column]
            if neuron_id in lookup:
                neurons[lookup[neuron_id]].update(side=side,celltype=row.get('celltype',''),
                    annotations=row.get('additional_annotations',''),cluster=row.get('level_7_cluster',''))
    args.out.mkdir(parents=True,exist_ok=True); sparse.save_npz(args.out/'winding_l1_connectome.npz',weights,compressed=True)
    (args.out/'groups.json').write_text(json.dumps(groups,indent=2),encoding='utf-8')
    (args.out/'neurons.json').write_text(json.dumps(neurons,indent=2),encoding='utf-8')
    print(f'Saved {weights.shape[0]} neurons, {weights.nnz:,} nonzero connections; groups:',{k:len(v) for k,v in groups.items()})

if __name__=='__main__': main()
