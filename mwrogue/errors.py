class EsportsCacheKeyError(KeyError):
    def __init__(self, file, value, length, value_table):
        self.file = file
        self.value = value
        self.length = length
        self.value_table = value_table
        self.allowed_keys = value_table.keys()

    def __str__(self):
        return "Invalid length of {} requested for {} in {}. Allowed: {}".format(
            self.length,
            self.value,
            self.file,
            ', '.join(self.allowed_keys)
        )


class EsportsCacheTeamnameKeyError(KeyError):
    def __init__(self, value, prop, value_table):
        self.value = value
        self.prop = prop
        self.value_table = value_table
        self.allowed_keys = value_table.keys()

    def __str__(self):
        return "Invalid prop of {} requested for {}. Allowed {}".format(
            self.prop,
            self.value,
            ', '.join(self.allowed_keys)
        )


class CantFindMatchHistory(KeyError):
    def __str__(self):
        return "Cannot find any valid tournament for provided match history. It may be missing from the MatchSchedule data, or there may be an issue with the parser."


class InvalidEventError(KeyError):
    def __str__(self):
        return "Invalid page name provided for event"
