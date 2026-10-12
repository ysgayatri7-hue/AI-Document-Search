import math
from statistics import median

def retrieval_metrics(ranked:list[str],relevant:set[str],k:int)->dict[str,float|None]:
    top=ranked[:k];hits=[x for x in top if x in relevant];reciprocal=next((1/(i+1) for i,x in enumerate(ranked) if x in relevant),0.0)
    return {"recall_at_k":len(set(hits))/len(relevant) if relevant else None,"precision_at_k":len(hits)/k if k else None,"mrr":reciprocal}

def binary_metrics(predicted:list[bool],labels:list[bool])->dict[str,float|None]:
    tp=sum(p and y for p,y in zip(predicted,labels));fp=sum(p and not y for p,y in zip(predicted,labels));fn=sum(not p and y for p,y in zip(predicted,labels));tn=sum(not p and not y for p,y in zip(predicted,labels))
    precision=tp/(tp+fp) if tp+fp else None;recall=tp/(tp+fn) if tp+fn else None
    f1=2*precision*recall/(precision+recall) if precision is not None and recall is not None and precision+recall else None
    return {"precision":precision,"recall":recall,"f1":f1,"false_positive_rate":fp/(fp+tn) if fp+tn else None}

def latency_metrics(values:list[float])->dict[str,float|None]:
    if not values:return {"median_ms":None,"p95_ms":None}
    ordered=sorted(values);return {"median_ms":median(ordered),"p95_ms":ordered[min(len(ordered)-1,math.ceil(.95*len(ordered))-1)]}

