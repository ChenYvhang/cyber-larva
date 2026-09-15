"""Derive kinematic targets from Schleyer experimental larva tracks.

Input CSV layout follows the G-Node/Larvaworld Schleyer dataset: frame index,
12 rear-to-front spine points, contour, summary values, and a contact flag.
Raw CC BY-NC-SA files stay outside the repository; only aggregate statistics
and provenance are written to config/trajectory_calibration.json.
"""
from pathlib import Path
import argparse, json
import numpy as np
from scipy.signal import find_peaks, periodogram, savgol_filter

FPS=16.0

def robust_frequency(x, lo, hi):
    f,p=periodogram(x-np.nanmean(x),fs=FPS)
    mask=(f>=lo)&(f<=hi)
    return float(f[mask][np.argmax(p[mask])]) if np.any(mask) else float('nan')

def track_metrics(path):
    a=np.genfromtxt(path,delimiter=',',dtype=np.float64,invalid_raise=False)
    spine=a[:,1:25].reshape(-1,12,2)
    finite=np.isfinite(spine).all(axis=(1,2))
    flags=a[finite,77];spine=spine[finite]
    valid=flags==0
    center=np.nanmean(spine,axis=1)
    for j in range(2):center[:,j]=savgol_filter(center[:,j],9,2,mode='interp')
    body_length=np.sum(np.linalg.norm(np.diff(spine,axis=1),axis=2),axis=1)
    L=float(np.nanmedian(body_length[valid]))
    delta=np.diff(center,axis=0,prepend=center[:1]);speed=np.linalg.norm(delta,axis=1)*FPS/L
    tail=np.mean(spine[:,:3],axis=1);head=np.mean(spine[:,-3:],axis=1)
    theta=np.unwrap(np.arctan2((head-tail)[:,1],(head-tail)[:,0]));theta=savgol_filter(theta,9,2,mode='interp')
    omega=np.gradient(theta)*FPS
    # Head bend relative to the mid-body axis.
    neck=np.mean(spine[:,7:9],axis=1);hv=head-neck;bv=neck-tail
    bend=np.arctan2(hv[:,0]*bv[:,1]-hv[:,1]*bv[:,0],np.sum(hv*bv,axis=1))
    bend=savgol_filter(np.unwrap(bend),7,2,mode='interp')
    peaks,_=find_peaks(np.abs(bend),height=np.deg2rad(20),prominence=np.deg2rad(12),distance=int(FPS*.45))
    free_seconds=max(np.count_nonzero(valid)/FPS,1)
    moving=valid&(speed>.04)&(speed<2.5)&(np.abs(omega)<12)
    turning=moving&(np.abs(bend)>np.deg2rad(20))
    curvature=np.abs(omega[turning])/np.maximum(speed[turning],.04)
    return {'body_length_mm':L,'median_speed_bl_s':float(np.nanmedian(speed[moving])),
            'p95_speed_bl_s':float(np.nanpercentile(speed[moving],95)),
            'crawl_frequency_hz':robust_frequency(speed[valid],1,2.5),
            'bend_frequency_hz':robust_frequency(bend[valid],.1,.8),
            'turn_curvature_rad_bl':float(np.nanmedian(curvature)) if len(curvature) else float('nan'),
            'head_cast_rate_hz':len(peaks)/free_seconds,
            'head_cast_angle_deg':float(np.nanmedian(np.abs(np.rad2deg(bend[peaks])))) if len(peaks) else float('nan'),
            'valid_seconds':free_seconds}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('tracks',nargs='+',type=Path);ap.add_argument('--out',type=Path,default=Path('config/trajectory_calibration.json'));args=ap.parse_args()
    rows=[track_metrics(p) for p in args.tracks]
    keys=[k for k in rows[0] if k!='valid_seconds']
    aggregate={k:float(np.nanmedian([r[k] for r in rows])) for k in keys}
    aggregate['n_tracks']=len(rows);aggregate['total_valid_seconds']=float(sum(r['valid_seconds'] for r in rows))
    out={'schema_version':1,'source':{'name':'Locomotion of naive Drosophila larvae','authors':'Thoener & Schleyer','doi':'10.12751/g-node.5e1ifd','repository':'https://github.com/nawrotlab/larvaworld/tree/master/src/larvaworld/data/SchleyerGroup/raw/exploration','license':'CC BY-NC-SA 4.0','sampling_hz':FPS},'empirical':aggregate,'per_track':rows,
         'published_crosscheck':{'source':'Sakagiannis et al., eLife 2026, Table 1','crawl_frequency_hz':1.42,'max_speed_bl_s':.51,'stride_distance_bl':.24,'turn_frequency_hz':.4,'body_length_mm':4.0,'crawl_turn_suppression':.46,'turn_relief':.54,'turn_relief_phase_rad':2.05}}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps(aggregate,indent=2))

if __name__=='__main__':main()
