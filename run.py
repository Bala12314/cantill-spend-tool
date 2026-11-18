import argparse, json, os, re, time, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC

ROOT=Path(__file__).resolve().parents[2]

def norm(s):
    s='' if pd.isna(s) else str(s).upper()
    s=re.sub(r'[^A-Z0-9]+',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def stable(prefix, s):
    return prefix+'-'+hashlib.sha1(norm(s).encode()).hexdigest()[:10]

def first(x):
    return x.iloc[0] if len(x) else None

def canon_item(x):
    s='' if pd.isna(x) else str(x)
    m=re.search(r'([0-9]+)(?:\.0+)?$',s.strip())
    return m.group(1) if m else norm(s)

def build_taxonomy(path):
    t=pd.read_csv(path).fillna('')
    cols=[c for c in t.columns if str(c).lower().startswith('category_') or str(c).lower() in {'l1','l2','l3','l4'}]
    if not cols:
        cols=list(t.columns)
    cols=cols[:4]
    return t[cols].drop_duplicates(), cols

def text_cols(df, cols):
    out=[]
    for c in cols:
        if c in df.columns: out.append(df[c].fillna('').astype(str))
    return pd.concat(out,axis=1).agg(' '.join,axis=1) if out else pd.Series('',index=df.index)

def classifier(train_text, train_y):
    # Prototype classifier: aggregate examples by label, then compare each input to
    # the label prototype. This keeps inference linear in the number of rows and
    # avoids an expensive all-pairs fuzzy search.
    tmp=pd.DataFrame({'text':train_text.fillna('').astype(str).values,'y':pd.Series(train_y).astype(str).values})
    proto=tmp.groupby('y',sort=False)['text'].apply(lambda s:' '.join(s.head(500))).reset_index()
    vec=TfidfVectorizer(ngram_range=(1,2), min_df=1, max_features=12000, sublinear_tf=True)
    Xp=vec.fit_transform(proto.text)
    return vec, (proto.y.to_numpy(), Xp)

def predict(vec, model, text):
    labels, Xp=model
    X=vec.transform(text.fillna('').astype(str))
    scores=X @ Xp.T
    scores=np.asarray(scores.toarray())
    order=np.argsort(scores,axis=1)
    best=order[:,-1]
    pred=labels[best]
    if scores.shape[1]>1:
        margin=scores[np.arange(len(scores)),best]-scores[np.arange(len(scores)),order[:,-2]]
    else: margin=scores[np.arange(len(scores)),best]
    conf=np.clip(0.5+margin,0,1)
    return pred, conf

def a_pipeline(cfg):
    d=cfg['data_dir']; out=Path(cfg['output'])
    erp=pd.read_csv(d+'/erp_goods_receipts.csv')
    tool=pd.read_csv(d+'/invoice_tool_export.csv')
    labels=pd.read_csv(d+'/labels_A.csv')
    tax,tcols=build_taxonomy(d+'/taxonomy_A.csv')
    labels=labels.set_index('record_id')
    erp['record_id']='ERP:'+erp.line_id.astype(str)
    erp['include']=1; erp['exclusion_reason']=''
    # ERP values are already net of tax per task brief.
    erp['spend']=pd.to_numeric(erp.value_zar,errors='coerce').fillna(0.0)
    erp['supplier_key']=erp.record_id.map(labels.supplier_key).fillna(erp.supplier_name.map(lambda x: stable('SG',x)))
    erp['item_key']=erp.record_id.map(labels.item_key).fillna(erp.material_number.map(lambda x: stable('IG',x)))
    # Use supplied labels for A ERP classification.
    for j,c in enumerate(tcols,1):
        erp[f'l{j}']=erp.record_id.map(labels[c]).fillna('')
    for j in range(len(tcols)+1,5): erp[f'l{j}']=''
    erp['confidence']=1.0

    # Tool duplicate invoice handling: first occurrence retained, later copies excluded.
    tool['record_id']='TOOL:'+tool.tool_record_id.astype(str)
    dup=tool.invoice_number.fillna('').astype(str).str.strip().ne('') & tool.invoice_number.fillna('').astype(str).duplicated(keep='first')
    tool['include']=1; tool['exclusion_reason']=''
    tool.loc[dup,'include']=0; tool.loc[dup,'exclusion_reason']='DUPLICATE'
    status=tool.status.fillna('').astype(str).str.lower()
    bad=status.isin(['cancelled','rejected','not approved','unapproved'])
    tool.loc[bad,'include']=0; tool.loc[bad,'exclusion_reason']='NOT_APPROVED'
    vat=pd.to_numeric(tool.vat_rate,errors='coerce').fillna(0.15)
    gross=pd.to_numeric(tool.gross_amount,errors='coerce').fillna(0.0)
    tool['spend']=gross/(1+vat)

    # Fast cross-system match: PO reference -> ERP PO + item, then exact normalized text.
    erp_po={}
    for i,r in erp.iterrows():
        po=norm(r.po_number); item=canon_item(r.po_item)
        if po: erp_po.setdefault((po,item),i)
    erp_text={}
    for i,r in erp.iterrows():
        txt=norm(str(r.material_short_text)+' '+str(r.service_short_text))
        if txt: erp_text.setdefault(txt,i)
    tool_supplier_norm=tool.supplier_name_as_captured.map(norm)
    tool_desc=tool.line_text.map(norm)
    matched=[]
    for i,r in tool.iterrows():
        ref='' if pd.isna(r.po_reference) else str(r.po_reference)
        m=re.search(r'(\d{7,})\s*/\s*([0-9]+(?:\.0)?)',ref)
        idx=None
        if m: idx=erp_po.get((m.group(1),canon_item(m.group(2))))
        if idx is None and tool_desc.iloc[i]: idx=erp_text.get(tool_desc.iloc[i])
        matched.append(idx)
    # derive supplier/item from ERP match where available, otherwise normalized source values
    sup=[]; item=[]
    for i,idx in enumerate(matched):
        if idx is not None:
            sup.append(erp.iloc[idx].supplier_key); item.append(erp.iloc[idx].item_key)
        else:
            sup.append(stable('SG',tool_supplier_norm.iloc[i])); item.append(stable('IG',tool_desc.iloc[i]))
    tool['supplier_key']=sup; tool['item_key']=item

    # Train classifier from A labels, then classify tool-only records.
    train_text=text_cols(erp,[ 'material_short_text','service_short_text','supplier_name','spend_type'])
    y=erp['l3'].where(erp['l3']!='',erp['l2'])
    vec,clf=classifier(train_text,y)
    pred,conf=predict(vec,clf,text_cols(tool,['line_text','supplier_name_as_captured']))
    # Map leaf predictions to taxonomy rows and reconstruct parents.
    tax_leaf={norm(r[tcols[-1]]):r for _,r in tax.iterrows()}
    for j,c in enumerate(tcols,1): tool[f'l{j}']=''
    for i,p in enumerate(pred):
        row=tax_leaf.get(norm(p))
        if row is not None:
            for j,c in enumerate(tcols,1): tool.iat[i,tool.columns.get_loc(f'l{j}')]=row[c]
        else: tool.iat[i,tool.columns.get_loc('l'+str(len(tcols)))]=p
    tool['confidence']=conf

    cols=['record_id','include','exclusion_reason','supplier_key','item_key','spend']+[f'l{i}' for i in range(1,5)]+['confidence']
    outdf=pd.concat([erp,tool],ignore_index=True)[cols]
    out.parent.mkdir(parents=True,exist_ok=True); outdf.to_csv(out,index=False)
    return {'rows':len(outdf),'duplicates':int(dup.sum()),'tool_matched_to_erp':int(sum(x is not None for x in matched))}

def b_pipeline(cfg):
    d=cfg['data_dir']; out=Path(cfg['output'])
    b=pd.read_csv(d+'/invoice_lines.csv'); seed=pd.read_csv(d+'/seed_labels.csv'); tax,tcols=build_taxonomy(d+'/taxonomy_B.csv'); fx=pd.read_csv(d+'/fx_rates_usd.csv')
    seed=seed.set_index('line_id')
    b['record_id']=b.line_id.astype(str)
    # Seed inclusion labels are authoritative for training; infer the rest from text/GL.
    seed_inc=seed.include.astype(int)
    train_df=b[b.line_id.isin(seed.index)].copy(); train_df=train_df.set_index('line_id')
    train_text=text_cols(train_df,['line_description','gl_account_description','supplier_type','document_type'])
    vec_inc,clf_inc=classifier(train_text,seed_inc.reindex(train_df.index).fillna(1))
    pred_inc,inc_conf=predict(vec_inc,clf_inc,text_cols(b,['line_description','gl_account_description','supplier_type','document_type']))
    b['include']=pred_inc.astype(int); b['exclusion_reason']=''
    # Preserve known seed labels exactly.
    known=set(seed.index)
    for i,r in b.iterrows():
        if r.line_id in known:
            b.at[i,'include']=int(seed.loc[r.line_id,'include'])
            b.at[i,'exclusion_reason']=str(seed.loc[r.line_id,'exclusion_reason'] or '')
    b.loc[b.include.eq(0) & b.exclusion_reason.eq(''),'exclusion_reason']='NON_PROCUREMENT'
    # B currency_rate is units of currency per USD; fallback monthly rate.
    amt=pd.to_numeric(b.line_amount,errors='coerce').fillna(0.0)
    cur=b.currency.fillna('USD').astype(str).str.upper()
    rate=pd.to_numeric(b.currency_rate,errors='coerce')
    months=pd.to_datetime(b.posting_date,errors='coerce').dt.strftime('%Y-%m')
    fxmap={(str(r.currency).upper(),str(r.month)):float(r.units_per_usd) for _,r in fx.iterrows()}
    rates=[]
    for i in range(len(b)):
        rr=rate.iloc[i]
        if pd.isna(rr): rr=fxmap.get((cur.iloc[i],months.iloc[i]),1.0)
        rates.append(rr if rr and rr!=0 else 1.0)
    b['spend']=amt/np.array(rates)
    b['supplier_key']=b.vendor_id.map(lambda x: stable('SG',x))
    # Replace item key fallback with normalized description deterministically.
    b['item_key']=b.material_number.map(lambda x: stable('IG',x) if norm(x) else '').astype(object)
    mask=b.item_key.eq(''); b.loc[mask,'item_key']=b.loc[mask,'line_description'].map(lambda x:stable('IG',x))
    # Category model from seed included rows.
    inc_train=train_df.loc[train_df.index.intersection(seed.index)].copy()
    inc_train=inc_train[seed.loc[inc_train.index,'include'].astype(int).eq(1)]
    cat_text=text_cols(inc_train,['line_description','gl_account_description','supplier_type','document_type'])
    leaf=seed.loc[inc_train.index,tcols[-1]].fillna('').astype(str)
    good=leaf.ne('')
    vec_cat,clf_cat=classifier(cat_text[good],leaf[good])
    pred,conf=predict(vec_cat,clf_cat,text_cols(b,['line_description','gl_account_description','supplier_type','document_type']))
    for j,c in enumerate(tcols,1): b[f'l{j}']=''
    for j in range(len(tcols)+1,5): b[f'l{j}']=''
    tax_leaf={norm(r[tcols[-1]]):r for _,r in tax.iterrows()}
    for i,p in enumerate(pred):
        row=tax_leaf.get(norm(p))
        if row is not None:
            for j,c in enumerate(tcols,1): b.iat[i,b.columns.get_loc(f'l{j}')]=row[c]
        else: b.iat[i,b.columns.get_loc('l'+str(len(tcols)))]=p
    b['confidence']=conf
    # Seed category labels are retained exactly where present.
    for idx in seed.index.intersection(b.line_id):
        bi=b.index[b.line_id.eq(idx)][0]
        for j,c in enumerate(tcols,1):
            val=seed.loc[idx,c] if c in seed.columns else ''
            if pd.notna(val) and str(val): b.at[bi,f'l{j}']=val
    cols=['record_id','include','exclusion_reason','supplier_key','item_key','spend']+[f'l{i}' for i in range(1,5)]+['confidence']
    out.parent.mkdir(parents=True,exist_ok=True); b[cols].to_csv(out,index=False)
    return {'rows':len(b),'seed_rows':len(seed),'excluded':int((b.include==0).sum())}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',required=True); args=ap.parse_args()
    t=time.time(); cfg=json.load(open(args.config))
    results=[]
    for name,c in cfg['companies'].items():
        if name=='A': results.append((name,a_pipeline(c)))
        elif name=='B': results.append((name,b_pipeline(c)))
        else: raise ValueError(f'Unsupported company in build config: {name}')
    print(json.dumps({'elapsed_seconds':round(time.time()-t,2),'results':dict(results)},indent=2))

if __name__=='__main__': main()
