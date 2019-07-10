import tensorflow as tf
import numpy as np
from makiflow.layers import Layer,ConvLayer, ActivationLayer, MaxPoolLayer
from makiflow.save_recover.activation_converter import ActivationConverter

# Reference: https://arxiv.org/pdf/1602.07261.pdf

class InceptionC(Layer):

	def __init__(self,in_f,out_f=[192,224,256,2144],activation=tf.nn.relu,name='inception_c'):
		"""
		Parameters
		----------
		in_f : int
			Number of the input feature maps relative to the first convolution in the block.
		out_f : list of int
			Numbers of the outputs feature maps of the convolutions in the block.
			out_f = [
				Conv1,
				Conv2,
				Conv3,
			]

		Notes
		-----
			Data flow scheme: 
			(left)    /----------->Conv1(1x1)--------------->|
			input--->|									     |+(concate)-->Conv(1x1)=last_conv_output
			(right)	  \->Conv1(1x1)->Conv2(1x3)->Conv3(3x1)->|
			Where two branches are summed together:
			final_output = input+last_conv_output.
		"""
		assert(len(out_f) == 3)
		Layer.__init__(self)
		self.name = name
		self.in_f = in_f
		self.out_f = out_f
		self.f = activation
		# Left branch
		self.conv_L_1 = ConvLayer(kw=1,kh=1,in_f=in_f,out_f=out_f[0],activation=None,name=name+'conv_L_1')
		# Right branch
		self.conv_R_1 = ConvLayer(kw=1,kh=1,in_f=in_f,out_f=out_f[0],activation=None,name=name+'conv_R_1')
		self.conv_R_2 = ConvLayer(kw=1,kh=3,in_f=out_f[0],out_f=out_f[1],activation=activation,name=name+'conv_R_2')
		self.conv_R_3 = ConvLayer(kw=3,kh=1,in_f=out_f[1],out_f=out_f[2],activation=activation,name=name+'conv_R_3')

		# Concate branch
		self.conv_after_conc = ConvLayer(kw=1,kh=1,in_f=out_f[2] + out_f[0],out_f=in_f,activation=None,name=name+'conv_after_conc')
		
		self.layers = [
			self.conv_L_1,
			self.conv_R_1,self.conv_R_2,self.conv_R_3,
			self.conv_after_conc,
		]

		self.named_params_dict = {}
		
		for layer in self.layers:
			self.named_params_dict.update(layer.get_params_dict())



	def forward(self,X,is_training=False):
		FX = X

		# Left
		LX = self.conv_L_1.forward(FX,is_training)
		# Right
		RX = self.conv_R_1.forward(FX,is_training)
		RX = self.conv_R_2.forward(RX,is_training)
		RX = self.conv_R_3.forward(RX,is_training)

		# Concate
		FX = tf.concat([LX,RX],axis=3)
		FX = self.conv_after_conc.forward(FX,is_training)
		
		return FX + X

	def get_params(self):
		params = []
		for layer in self.layers:
			params += layer.get_params()
		return params
	
	def get_params_dict(self):
		return self.named_params_dict



	def to_dict(self):
		return {
			'type':'ResnetInceptionBlockC',
			'params':{
				'name': self.name,
				'in_f': self.in_f,
				'out_f': self.out_f,
				'activation': ActivationConverter.activation_to_str(self.f),
			}
		}