import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.layers import Dense, Flatten, Conv2D, BatchNormalization, LeakyReLU, Reshape, Conv2DTranspose
from preprocess import load_image_batch
import tensorflow_gan as tfgan
import tensorflow_hub as hub
from preprocessing import *

import numpy as np

from imageio import imwrite
import os
import argparse
import sys

# Killing optional CPU driver warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

gpu_available = tf.test.is_gpu_available()
print("GPU Available: ", gpu_available)

## --------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='DCGAN')

parser.add_argument('--img-dir', type=str, default='./data/celebA',
                    help='Data where training images live')

parser.add_argument('--out-dir', type=str, default='./output',
                    help='Data where sampled output images will be written')

parser.add_argument('--mode', type=str, default='train',
                    help='Can be "train" or "test"')

parser.add_argument('--restore-checkpoint', action='store_true',
                    help='Use this flag if you want to resuming training from a previously-saved checkpoint')

parser.add_argument('--z-dim', type=int, default=100,
                    help='Dimensionality of the latent space')

parser.add_argument('--batch-size', type=int, default=128,
                    help='Sizes of image batches fed through the network')

parser.add_argument('--num-data-threads', type=int, default=2,
                    help='Number of threads to use when loading & pre-processing training images')

parser.add_argument('--num-epochs', type=int, default=10,
                    help='Number of passes through the training data to make before stopping')

parser.add_argument('--learn-rate', type=float, default=0.0002,
                    help='Learning rate for Adam optimizer')

parser.add_argument('--beta1', type=float, default=0.5,
                    help='"beta1" parameter for Adam optimizer')

parser.add_argument('--num-gen-updates', type=int, default=2,
                    help='Number of generator updates per discriminator update')

parser.add_argument('--log-every', type=int, default=7,
                    help='Print losses after every [this many] training iterations')

parser.add_argument('--save-every', type=int, default=500,
                    help='Save the state of the network after every [this many] training iterations')

parser.add_argument('--device', type=str, default='GPU:0' if gpu_available else 'CPU:0',
                    help='specific the device of computation eg. CPU:0, GPU:0, GPU:1, GPU:2, ... ')

args = parser.parse_args()



class SCAE(tf.keras.Model):
    def __init__():

        self.learning_rate = 0.01
        self.optimizer = tf.keras.optimizers.Adam(learning_rate=self.learning_rate)
        self.batch_size = 128
        self.epoch = 1

        # Conv2D(64, (3, 3), activation='relu', padding='same')
        self.conv_layer1 = Conv2D(filters=64, strides=(2,2), activation='relu', padding='same', name='conv_layer1')
        self.conv_layer2 = Conv2D(filters=128, stries=(2,2), activation='relu', padding='same', name='conv_layer2')
        self.deconv_layer1 = Conv2DTranspose(filters=64, strides=(2,2), activation='relu', padding='same', name='deconv_layer1')
        self.deconv_layer2 = Conv2DTranspose(filters=1, strides=(2,2), activation='relu', padding='same', name='deconv_layer2')


    def call(self, inputs):
        c1 = self.conv_layer1(inputs)
#         c1 = tf.nn.max_pool(c1, [1, 2, 2 ,1], 2, self.padding) #? idk
        c2 = self.conv2_layer2(c1)

        d1 = self.deconv_layer1(d1)
        # paper says unpool, we say not now
        d2 = self.deconv_layer(d1)
        return d2

    def loss(original, decoded):
        return tf.reduce_sum((original-decoded)**2) / original.shape[0]

def train(model, images):
    batches = images.shape[0] / model.batch_size

    for i in range(batches):
        image_inputs = images[i * model.batch_size : (i+1) * model.batch_size]

        with tf.GradientTape() as tape:
            res = model(image_inputs)
            loss = model.loss(image_inputs, res)

        gradient = tape.gradient(loss, model.trainable_variables)
        model.optimizer.apply_gradients(zip(gradients, model.trainable_variables))

def main():

    images = preprocess()
    #
    # model = SCAE()
    # for i in range(model.epoch):
    #     print("---EPOCH", i, "---")
    #     res = train(model, images)
    # Load a batch of images (to feed to the discriminator)

    # Initialize generator and discriminator models
    scae = SCAE()

    # For saving/loading models
    checkpoint_dir = './checkpoints'
    checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt")
    checkpoint = tf.train.Checkpoint(scae = scae)
    manager = tf.train.CheckpointManager(checkpoint, checkpoint_dir, max_to_keep=3)
    # Ensure the output directory exists
    if not os.path.exists(args.out_dir):
        os.makedirs(args.out_dir)

    if args.restore_checkpoint or args.mode == 'test':
        # restores the latest checkpoint using from the manager
        checkpoint.restore(manager.latest_checkpoint)

    try:
        # Specify an invalid GPU device
        with tf.device('/device:' + args.device):
            if args.mode == 'train':
                for epoch in range(0, args.num_epochs):
                    print('========================== EPOCH %d  ==========================' % epoch)
                    train(scae, images)
                    print("**** SAVING CHECKPOINT AT END OF EPOCH ****")
                    manager.save()
                    model.save_weights('./weights', save_format='tf')
            # if args.mode == 'test':
            #     test(scae)
    except RuntimeError as e:
        print(e)

if __name__== "__main__":
    main()
