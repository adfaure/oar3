# coding: utf-8
from procset import ProcSet

from oar.kao.slot import MAX_TIME, Slot, SlotSet, intersec_itvs_slots
from oar.lib.job_handling import JobPseudo


def compare_slots_val_ref(slots, v):
    sid = 1
    i = 0
    while True:
        slot = slots[sid]
        (b, e, itvs) = v[i]
        if (slot.b != b) or (slot.e != e) or not (slot.itvs == itvs):
            print("NOT EQUAL", sid, i, slot.b, b, slot.e, e, slot.itvs, itvs)
            return False
        sid = slot.next
        if sid == 0:
            break
        i += 1
    return True


def test_intersec_itvs_slots():
    s1 = Slot(1, 0, 2, ProcSet(*[(1, 32)]), 1, 10)
    s2 = Slot(2, 1, 3, ProcSet(*[(1, 16), (24, 28)]), 11, 20)
    s3 = Slot(3, 2, 0, ProcSet(*[(1, 8), (12, 26)]), 21, 30)

    slots = {1: s1, 2: s2, 3: s3}

    itvs = intersec_itvs_slots(slots, 1, 3)

    assert itvs == ProcSet(*[(1, 8), (12, 16), (24, 26)])


def test_split_slots_ab():
    v = [(1, 4, ProcSet(*[(1, 32)])), (5, 20, ProcSet(*[(1, 9), (21, 32)]))]

    j1 = JobPseudo(
        id=1,
        start_time=5,
        walltime=20,
        res_set=ProcSet(*[(10, 20)]),
        moldable_id=1,
        ts=False,
        ph=0,
    )

    ss = SlotSet(Slot(1, 0, 0, ProcSet(*[(1, 32)]), 1, 20))
    ss.split_slots(1, 1, j1)
    assert compare_slots_val_ref(ss.slots, v)


def test_split_slots_abc():
    v = [
        (1, 4, ProcSet(*[(1, 32)])),
        (5, 14, ProcSet(*[(1, 9), (21, 32)])),
        (15, 20, ProcSet(*[(1, 32)])),
    ]

    j1 = JobPseudo(
        id=1,
        start_time=5,
        walltime=10,
        res_set=ProcSet(*[(10, 20)]),
        moldable_id=1,
        ts=False,
        ph=0,
    )

    ss = SlotSet(Slot(1, 0, 0, ProcSet(*[(1, 32)]), 1, 20))
    ss.split_slots(1, 1, j1)
    assert compare_slots_val_ref(ss.slots, v)


def test_split_slots_b():
    v = [(1, 20, ProcSet(*[(1, 9), (21, 32)]))]

    j1 = JobPseudo(
        id=1,
        start_time=1,
        walltime=21,
        res_set=ProcSet(*[(10, 20)]),
        moldable_id=1,
        ts=False,
        ph=0,
    )

    ss = SlotSet(Slot(1, 0, 0, ProcSet(*[(1, 32)]), 1, 20))
    ss.split_slots(1, 1, j1)
    assert compare_slots_val_ref(ss.slots, v)


def test_split_slots_bc():
    v = [(1, 10, ProcSet(*[(1, 9), (21, 32)])), (11, 20, ProcSet(*[(1, 32)]))]

    j1 = JobPseudo(
        id=1,
        start_time=1,
        walltime=10,
        res_set=ProcSet(*[(10, 20)]),
        moldable_id=1,
        ts=False,
        ph=0,
    )

    ss = SlotSet(Slot(1, 0, 0, ProcSet(*[(1, 32)]), 1, 20))
    ss.split_slots(1, 1, j1)
    assert compare_slots_val_ref(ss.slots, v)


def test_bug_split_slots():
    v = [
        (20, 69, ProcSet(*[(31, 32)])),
        (70, 79, ProcSet(*[(1, 15), (31, 32)])),
        (80, 2147483599, ProcSet(*[(1, 32)])),
        (2147483600, 2147483647, ProcSet()),
    ]

    # res = [(1, 32)]
    s1 = Slot(1, 0, 4, ProcSet(*[(16, 32)]), 20, 69)
    s2 = Slot(2, 1, 0, ProcSet(), 2147483600, 2147483647)
    s4 = Slot(4, 1, 2, ProcSet(*[(1, 32)]), 70, 2147483599)

    slts = dict(((s.id, s) for s in [s1, s2, s4]))
    ss = SlotSet(slts)

    j2 = JobPseudo(
        id=2, start_time=20, walltime=60, res_set=ProcSet(*[(16, 30)]), ts=False, ph=0
    )

    ss.split_slots(1, 4, j2)
    assert compare_slots_val_ref(ss.slots, v)


def test_add_split_slots_jobs_one_job():
    v = [(10, 14, ProcSet(*[(10, 50)])), (15, MAX_TIME, ProcSet())]

    ss = SlotSet((ProcSet(*[]), 10))

    j = JobPseudo(
        id=1, start_time=5, walltime=10, res_set=ProcSet(*[(10, 50)]), ts=False, ph=0
    )

    ss.split_slots_jobs([j], False)

    assert compare_slots_val_ref(ss.slots, v)


def test_add_split_slots_jobs_2_jobs_1():
    v = [
        (10, 19, ProcSet()),
        (20, 99, ProcSet(*[(40, 50)])),
        (100, 129, ProcSet(*[(10, 20), (40, 50)])),
        (130, 219, ProcSet(*[(40, 50)])),
        (220, MAX_TIME, ProcSet()),
    ]

    ss = SlotSet((ProcSet(*[]), 10))

    j1 = JobPseudo(
        id=1, start_time=100, walltime=30, res_set=ProcSet(*[(10, 20)]), ts=False, ph=0
    )

    j2 = JobPseudo(
        id=2, start_time=20, walltime=200, res_set=ProcSet(*[(40, 50)]), ts=False, ph=0
    )

    ss.split_slots_jobs([j1], False)

    ss.split_slots_jobs([j2], False)

    assert compare_slots_val_ref(ss.slots, v)


def test_add_split_slots_jobs_2_jobs_2():
    v = [
        (10, 19, ProcSet()),
        (20, 99, ProcSet(*[(40, 50)])),
        (100, 129, ProcSet(*[(10, 20), (40, 50)])),
        (130, 219, ProcSet(*[(40, 50)])),
        (220, MAX_TIME, ProcSet()),
    ]

    ss = SlotSet((ProcSet(*[]), 10))

    j1 = JobPseudo(
        id=1, start_time=100, walltime=30, res_set=ProcSet(*[(10, 20)]), ts=False, ph=0
    )

    j2 = JobPseudo(
        id=2, start_time=20, walltime=200, res_set=ProcSet(*[(40, 50)]), ts=False, ph=0
    )

    ss.split_slots_jobs([j2, j1], False)

    assert compare_slots_val_ref(ss.slots, v)
