#!/usr/bin/env python3
"""Create a fresh profile marker matching the locally prepared ISO configuration."""
from pathlib import Path
import argparse,json,uuid
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('destination',type=Path,help='New LiveProfile directory; copy to your USB afterwards')
args=parser.parse_args()
marker={'version':1,'id':str(uuid.UUID((root/'.local/profile-id').read_text().strip()))}
args.destination.mkdir(parents=True,exist_ok=True)
path=args.destination/'store.json'
with path.open('x',encoding='utf-8') as stream:stream.write(json.dumps(marker,indent=2)+'\n')
print('Created '+str(path))
