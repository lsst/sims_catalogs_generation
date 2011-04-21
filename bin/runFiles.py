import sys, os, time
import pyoorb
import lsst.sims.catalogs.generation.utils.runTrimCat as rtc
from lsst.sims.catalogs.generation.db import jobDB

def getIds(offset, number, fhids):
  ids = []
  for i,line in enumerate(fhids):
    if i >= offset and i < offset+number:
      flds = line.rstrip().split()
      ids.append(int(flds[0]))
  fhids.close()
  return ids

def run(id, csize=50000, radius=2.1, outdir='/state/partition1/krughoff', repodir='/share/pogo3/krughoff/trimsPT1.2', compress=True, cleanup=False):
    je = jobDB.LogEvents("Test job number %i"%(id), jobid=id)
    print "Job number is %i"%(je._jobid)
    try:
        rtc.runTrim(csize, id, radius, outdir, repodir, je, compress=compress, cleanup=cleanup)
    except Exception, e:
        rtc.writeJobeEvent(je, "Exception", description=e.__str__())
        raise e

if __name__ == "__main__":
  run(int(sys.argv[1]), radius=float(sys.argv[2]), cleanup=True)
