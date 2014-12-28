from job import SET_PLACEHOLDER, USE_PLACEHOLDER
from interval import intersec, sub_intervals
from hierarchy import find_resource_hierarchies_scattered
from copy import deepcopy


class Slot:
    def __init__(self, id, prev, next, itvs, b, e, ts_itvs={}, ph_itvs={}):
        self.id = id
        self.prev = prev
        self.next = next
        self.itvs = itvs
        self.b = b
        self.e = e
        self.ts_itvs = ts_itvs #timesharing ts_itvs: [user] * [job_name] * itvs
        self.ph_itvs = ph_itvs #placeholder ph_itvs: [ph_name] * itvs
    def show(self):
        print "(id:", self.id, "p:", self.prev, "n:", self.next, ") itvs:",\
            self.itvs, "b:", self.b, "e:", self.e,\
            "ts_itvs:", self.ts_itvs, "ph_itvs:", self.ph_itvs

# not used TO REMOVE?
def intersec_slots(slots):
    'Return intersection of intervals from a slot list'
    return reduce(lambda itvs_acc, s: intersec(itvs_acc, s.itvs), slots, slots[0].itvs)

def intersec_itvs_slots(slots, sid_left, sid_right):
    sid = sid_left
    itvs_acc = slots[sid].itvs

    while (sid != sid_right):
        sid = slots[sid].next
        itvs_acc = intersec(itvs_acc, slots[sid].itvs)

    return itvs_acc

def intersec_ts_ph_itvs_slots(slots, sid_left, sid_right, job):
    
    sid = slots[sid_left].prev
    itvs_acc = []

    while (sid != sid_right):
        sid = slots[sid].next

        slot = slots[sid]
        itvs = slot.itvs
        
        if job.ts:
            if "*" in slot.ts_itvs:
                if "*" in slot.ts_itvs["*"]:
                    itvs = add_interval(itvs, slot.ts_itvs["*"]["*"])
                elif  job.name in slot.ts_itvs["*"]:
                    itvs = add_interval(itvs, slot.ts_itvs["*"][job.name])
            elif job.user in slot.ts_itvs:
                if "*" in slot.ts_itvs[job.user]:
                    itvs = add_interval(itvs, slot.ts_itvs[job.user]["*"])
                elif  job.name in slot.ts_itvs[job.user]:
                    itvs = add_interval(itvs, slot.ts_itvs[job.user][job.name])
                    
        if job.ph == USE_PLACEHOLDER:
            if job.ph_name in slot.ph_itvs:
                itvs = add_interval(itvs, slot.ph_itvs[job.ph_name])
        

        itvs_acc = intersec(itvs_acc, itvs)
        
    return itvs_acc

class SlotSet:

    def __init__(self, first_slot, slots = {} ):
        if (first_slot != None):
            self.slots = {1: first_slot}
            self.last_id = 1
        else:
            self.slots = slots
            s = slots[1]
            while (s.next !=0):
                s = slots[s.next]
            self.last_id = s.id

        #  cache the last sid_left given for by walltime => not used
        # cache the last sid_left given for same previous job
        #  (same requested resources w/ constraintes)
        self.cache = {}

    def show_slots(self):
        for i, slot in self.slots.iteritems():
            print i
            slot.show()
        print '---'

    #
    # split slot accordingly with job resource assignment *)
    # new slot A + B + C (A, B and C can be null)         *)
    #   -------
    #   |A|B|C|
    #   |A|J|C|
    #   |A|B|C|
    #   -------

    # generate A slot - slot before job's begin
    def slot_before_job(self, slot, job):
        s_id = slot.id
        self.last_id += 1
        n_id = self.last_id
        a_slot = Slot(s_id, slot.prev, n_id, slot.itvs[:], slot.b, job.start_time-1,
                      deepcopy(slot.ts_itvs), slot.ph_itvs )
        slot.prev = s_id
        self.slots[s_id] = a_slot
        #slot_id is changed so we have always the rightmost slot (min slot.b) w/ sid = 1 r
        slot.id = n_id
        self.slots[n_id] = slot

    # generate B slot
    def slot_during_job(self, slot, job):
        slot.b = max(slot.b, job.start_time)
        slot.e = min(slot.e, job.start_time + job.walltime - 1)
        slot.itvs = sub_intervals(slot.itvs, job.res_set)
        if job.ts:
            if not slot.ts_itvs[job.user]:
                slot.ts_itvs[job.user] = {}
            slot.ts_itvs[job.user][job.name] = job.res_set[:] 
        
        if job.ph == USE_PLACEHOLDER:
            if slot.ph_itvs[job.ph_name]:
                slot.ph_itvs[job.ph_name] = sub_interval(slot.ph_itvs[job.ph_name], job.res_set)

        if job.ph == SET_PLACEHOLDER:
            slot.ph_itvs[job.ph_name] = job.res_set[:]

    # generate C slot - slot after job's end
    def slot_after_job(self, slot, job):
        self.last_id += 1
        s_id = self.last_id
        c_slot = Slot(s_id, slot.id, slot.next, slot.itvs[:], job.start_time + job.walltime, slot.e,
                      deepcopy(slot.ts_itvs), slot.ph_itvs )
        slot.next = s_id
        self.slots[s_id] = c_slot

    def split_slots(self, sid_left, sid_right, job):
        #        print "yop--->", sid_left, sid_right, job.start_time, job.walltime
        sid = sid_left
        while True:
            slot = self.slots[sid]
            #print "split", slot.show()
            if job.start_time > slot.b:
                # generate AB | ABC
                if ( job.start_time + job.walltime) > slot.e:
                    # generate AB
                    self.slot_before_job(slot, job)
                    self.slot_during_job(slot, job)
                else:
                    # generate ABC
                    self.slot_before_job(slot, job)
                    # generate C before modify slot / B
                    self.slot_after_job(slot, job)
                    self.slot_during_job(slot, job)

            else:
                # generate B | BC
                if ((job.start_time + job.walltime) - 1) >= slot.e:
                    # generate B
                    self.slot_during_job(slot, job)
                else:
                    # generate BC
                    # generate C before modify slot / B
                    self.slot_after_job(slot, job)
                    self.slot_during_job(slot, job)

            if (sid == sid_right):
                break
            else:
                sid = slot.next

#    def split_slots_prev_scheduled_one_job

    def split_slots_prev_scheduled_jobs(self, ordered_jobs):
        ''' function which insert previously occupied slots in slots
        job must be sorted by start_time
        used in kamelot for pseudo_jobs_resources_available_upto splitting'''
        slot = self.slots[1] # 1
        left_sid_2_split = 1
        right_sid_2_split = 1

        for job in ordered_jobs:
            # find_first_slot
            while not( (slot.b > job.start_time) or ((slot.b <= job.start_time) and (job.start_time <= slot.e)) ):
                left_sid_2_split = slot.next
                slot = self.slots[slot.next]

            right_sid_2_split = left_sid_2_split
            # find_slots_encompass
            while not (slot.e >=  (job.start_time + job.walltime)):
                right_sid_2_split = slot.next
                slot = self.slots[slot.next]

            #self.show_slots()
            #print "left_sid_2_split, right_sid_2_split", left_sid_2_split, right_sid_2_split
            #print job.__dict__
            self.split_slots(left_sid_2_split, right_sid_2_split, job)
