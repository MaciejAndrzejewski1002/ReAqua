__version__ = "3.0.0"
__authors__ = (
    "Maciej Andrzejewski",
    "Weronika Zator",
    "Kacper Mikołajczyk",
    "Tomasz Szulski",
)
__team_lead__ = "Maciej Andrzejewski"


def classFactory(iface):
    from .gui.plugin import ReAquaPlugin

    return ReAquaPlugin(iface)
