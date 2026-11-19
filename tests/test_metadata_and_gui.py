import configparser
import importlib
import os
import re
import sys
import types

import pytest

import reaqua
from reaqua.core import params

ROOT = os.path.dirname(os.path.dirname(__file__))
FORMER_AUTHORS = ("Maja Wochniak", "Ignacy Karasek")


def _text_files():
    for base in ("src", "docs", "tests"):
        for folder, _dirs, files in os.walk(os.path.join(ROOT, base)):
            for name in files:
                if name.endswith((".py", ".md", ".txt", ".html")):
                    yield os.path.join(folder, name)
    for name in ("README.md", "pyproject.toml", "AUTHORS"):
        path = os.path.join(ROOT, name)
        if os.path.exists(path):
            yield path


def test_authors_current_team():
    assert "Tomasz Szulski" in reaqua.__authors__
    assert len(reaqua.__authors__) == 4
    assert reaqua.__team_lead__ in reaqua.__authors__


def test_former_authors_not_listed_in_sources():
    this_file = os.path.abspath(__file__)
    for path in _text_files():
        if os.path.abspath(path) == this_file:
            continue
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        for name in FORMER_AUTHORS:
            assert name not in content, f"{name} w {path}"


def test_version_is_consistent():
    meta = configparser.ConfigParser()
    meta.read(os.path.join(ROOT, "src", "reaqua", "metadata.txt"), encoding="utf-8")
    with open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8") as fh:
        pyproject = fh.read()
    assert meta["general"]["version"] == reaqua.__version__
    assert re.search(rf'^version = "{re.escape(reaqua.__version__)}"', pyproject, re.M)
    for author in reaqua.__authors__:
        assert author in meta["general"]["author"]


def test_every_parameter_has_default_and_label():
    for spec in params.ALL_PARAMS:
        assert spec.key and spec.label
    merged = params.merge({})
    assert merged["kriging_type"] == "simple"
    assert all(spec.key in merged for spec in params.ALL_PARAMS)


class _Meta(type):
    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _Dummy()


class _Dummy(metaclass=_Meta):
    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return _Dummy()

    def __call__(self, *args, **kwargs):
        return _Dummy()


class _Recorder:
    def __init__(self):
        self.custom, self.removed_custom, self.menu, self.removed_menu = [], [], [], []

    def mainWindow(self):
        return None

    def addPluginToMenu(self, menu, action):
        self.menu.append((menu, action))

    def removePluginMenu(self, menu, action):
        self.removed_menu.append((menu, action))

    def addToolBarIcon(self, action):
        pass

    def removeToolBarIcon(self, action):
        pass

    def addCustomActionForLayerType(self, action, menu, layer_type, all_layers):
        self.custom.append((menu, layer_type, all_layers))

    def removeCustomActionForLayerType(self, action):
        self.removed_custom.append(action)


class _StubModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        value = _Meta(name, (_Dummy,), {})
        setattr(self, name, value)
        return value


@pytest.fixture()
def stubbed_qgis(monkeypatch):
    names = ("qgis", "qgis.core", "qgis.gui", "qgis.PyQt", "qgis.PyQt.QtCore", "qgis.PyQt.QtGui",
             "qgis.PyQt.QtWidgets")
    for name in names:
        monkeypatch.setitem(sys.modules, name, _StubModule(name))
    for mod in [m for m in sys.modules if m.startswith("reaqua.gui")]:
        monkeypatch.delitem(sys.modules, mod)
    yield
    for mod in [m for m in sys.modules if m.startswith("reaqua.gui")]:
        sys.modules.pop(mod, None)


def test_plugin_registers_context_menu(stubbed_qgis):
    plugin_module = importlib.import_module("reaqua.gui.plugin")
    iface = _Recorder()
    plugin = plugin_module.ReAquaPlugin(iface)
    plugin.initGui()
    assert len(iface.custom) == 6
    assert {menu for menu, _t, _a in iface.custom} == {"ReAqua"}
    assert len(iface.menu) == 5 and {m for m, _a in iface.menu} == {"&ReAqua"}
    plugin.unload()
    assert len(iface.removed_custom) == 6 and len(iface.removed_menu) == 5
    assert plugin.actions == [] and plugin.context_actions == []


def test_class_factory_returns_plugin(stubbed_qgis):
    plugin = reaqua.classFactory(_Recorder())
    assert type(plugin).__name__ == "ReAquaPlugin"
