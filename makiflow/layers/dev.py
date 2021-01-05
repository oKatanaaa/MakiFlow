# Copyright (C) 2020  Igor Kilbas, Danil Gribanov, Artem Mukhin
#
# This file is part of MakiFlow.
#
# MakiFlow is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MakiFlow is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Foobar.  If not, see <https://www.gnu.org/licenses/>.

from makiflow.core import MakiLayer
import tensorflow as tf


class ShapeLayer(MakiLayer):
    @staticmethod
    def build(params: dict):
        pass

    def __init__(self, name):
        super().__init__(name, [], [], {})

    def forward(self, x, computation_mode=MakiLayer.INFERENCE_MODE):
        return tf.shape(x)

    def training_forward(self, x):
        return self.forward(x, MakiLayer.TRAINING_MODE)

    def to_dict(self):
        pass


class IndexLayer(MakiLayer):
    @staticmethod
    def build(params: dict):
        pass

    def __init__(self, key, name):
        self._key = key
        super().__init__(name, [], [], {})

    def forward(self, x, computation_mode=MakiLayer.INFERENCE_MODE):
        return x[self._key]

    def training_forward(self, x):
        return self.forward(x, MakiLayer.TRAINING_MODE)

    def to_dict(self):
        pass
