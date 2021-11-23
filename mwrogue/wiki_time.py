from pytz import timezone, utc
from datetime import datetime


class WikiTime(object):
    """
    Leaguepedia and the other esports wikis use an EXTREMELY simplified time zone model.
    In this model, there are only three time zones: PST, CET, and KST.
    Additionally, the wiki itself does not know anything about daylight savings;
    instead, it relies on the user supplying DST metadata along with every timestamp.
    DST metadata can be supplied with three options: Yes, Spring [or Fall], or No.
    Yes means that both CET and PST have DST; No means that neither does, and
    Spring/Fall mean that PST does but CET does not. (KST, sanely, never has DST.)
    For simplicity, even in the fall, we return `Spring`.
    
    This class reduces timestamps to this simple model and provides information
    in the format expected by the esports wikis.
    """
    pst = timezone('America/Los_Angeles')
    cet = timezone('Europe/Berlin')
    kst = timezone('Asia/Seoul')
    
    def __init__(self, timestamp: datetime, tz: timezone = utc):
        """
        Creates a wiki date-time object

        :param timestamp: a datetime object
        :param tz: optional, a timezone. if not provided, utc will be assumed.
        """
        if timestamp.tzinfo is None:
            timestamp = tz.localize(timestamp)
        self.pst_object = timestamp.astimezone(self.pst)
        self.cet_object = timestamp.astimezone(self.cet)
        self.kst_object = timestamp.astimezone(self.kst)
        self.pst_date = self.pst_object.strftime('%Y-%m-%d')
        self.cet_date = self.cet_object.strftime('%Y-%m-%d')
        self.kst_date = self.kst_object.strftime('%Y-%m-%d')
        self.pst_time = self.pst_object.strftime('%H:%M')
        self.cet_time = self.cet_object.strftime('%H:%M')
        self.kst_time = self.kst_object.strftime('%H:%M')
        self.dst = self._determine_dst()
    
    def _determine_dst(self):
        is_dst_pst = self.pst_object.dst()
        is_dst_cet = self.cet_object.dst()
        if is_dst_pst and is_dst_cet:
            return 'yes'
        elif is_dst_pst:
            return 'spring'
        else:
            return 'no'
