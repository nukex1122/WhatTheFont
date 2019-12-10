import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.layers import Dense, Flatten, Conv2D, BatchNormalization, LeakyReLU, Reshape, Conv2DTranspose
import tensorflow_hub as hub
from collections import Counter
import numpy as np

import sys
sys.path.append('../data')

from imageio import imwrite
import os
import argparse
from preprocessing import *

# Killing optional CPU driver warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

gpu_available = tf.test.is_gpu_available()
print("GPU Available: ", gpu_available)


parser = argparse.ArgumentParser(description='DF_MODIFIED')


parser.add_argument('--mode', type=str, default='train',
					help='Can be "train" or "test"')

parser.add_argument('--restore-checkpoint', action='store_true',
					help='Use this flag if you want to resuming training from a previously-saved checkpoint')


parser.add_argument('--batch-size', type=int, default=128,
					help='Sizes of image batches fed through the network')


parser.add_argument('--num-epochs', type=int, default=10,
					help='Number of passes through the training data to make before stopping')

parser.add_argument('--learn-rate', type=float, default=0.0002,
					help='Learning rate for Adam optimizer')

parser.add_argument('--log-every', type=int, default=7,
					help='Print losses after every [this many] training iterations')

parser.add_argument('--save-every', type=int, default=500,
					help='Save the state of the network after every [this many] training iterations')

parser.add_argument('--device', type=str, default='GPU:0' if gpu_available else 'CPU:0',
					help='specific the device of computation eg. CPU:0, GPU:0, GPU:1, GPU:2, ... ')

args = parser.parse_args()



class DeepFont(tf.keras.Model): #is this how to convert to sequential?
    def __init__(self):
        """
        The model for the generator network is defined here.
        """
        super(DeepFont, self).__init__()
        self.batch_size = 256
        self.stride_size = 1
        self.num_classes = 150


        self.model = tf.keras.Sequential()

        self.model.add(tf.keras.layers.Reshape((96, 96, 1)))
        self.model.add(tf.keras.layers.Conv2D(trainable=False, filters=64, strides=(2,2), kernel_size=(3,3), padding='same', name='conv_layer1', input_shape=(96, 96,1))) #, input_shape=(args.batch_size,)
        self.model.add(tf.keras.layers.BatchNormalization())
        self.model.add(tf.keras.layers.MaxPooling2D(pool_size=(2,2), strides=None, padding='same'))

        self.model.add(tf.keras.layers.Conv2D(trainable=False, filters=128, strides=(1,1), kernel_size=(3,3), padding='same', name='conv_layer2'))
        self.model.add(tf.keras.layers.BatchNormalization())
        self.model.add(tf.keras.layers.MaxPooling2D(pool_size=(2,2), strides=None, padding='same'))

        self.model.add(tf.keras.layers.Conv2D(256, kernel_size=(3), strides=(self.stride_size), padding='same', activation='relu'))
        self.model.add(tf.keras.layers.Conv2D(512, kernel_size=(3,3), strides=(self.stride_size), padding='same', activation='relu'))
        self.model.add(tf.keras.layers.Conv2D(1024, kernel_size=(3,3), strides=(self.stride_size), padding='same', activation='relu'))
        self.model.add(tf.keras.layers.Conv2D(512, kernel_size=(3,3), strides=(self.stride_size), padding='same', activation='relu'))

        self.final_dense = tf.keras.layers.Dense(self.num_classes, activation='softmax')

        self.optimizer = tf.keras.optimizers.Adam(learning_rate = 0.01)

    def call(self, inputs):
        """
        Executes the generator model on the random noise vectors.

        :param inputs: a batch of random noise vectors, shape=[batch_size, num_classes]

        :return: logits for each batch image and its classification distribution
        """
        conv_layers =  self.model(inputs)
        reduced_cols = tf.reduce_mean(conv_layers, 1)
        reduced_rows =  tf.reduce_mean(reduced_cols, 1)
        result = self.final_dense(reduced_rows)

        return result

    def loss_function(self, probs, labels):
        loss = tf.keras.losses.sparse_categorical_crossentropy(labels, probs)
        return tf.math.reduce_mean(loss)

    def total_accuracy(self, probs, labels):
        """  given a batch of probs (batch size x 150) 
        and labels (batch size x 150)
        """
        print("----------total accuracy ----------")
        acc = 0

        top_five = np.argsort(probs, axis = 1) # 256 x 150
        top_five = np.array(top_five).reshape((self.batch_size, 150))
        top_five = top_five[:, -5:] # 5 x 150

        for i in range (len(labels)):
            if labels[i] in top_five[i]:
                acc += 1

        return acc / float(self.batch_size))

    def get_top_five(self, predictions):
        sums = np.sum(predictions, axis = 0) # sums the columns of the logits shape is (150,)
        print("SUMMED", sums)
        print("SUMEMD SHAPE ", sums.shape)

        probabilities = tf.nn.softmax(sums) # shape is (150, )
        print("PROBABILITIES: ", probabilities)

        top_five = np.argsort(probabilities, axis = 0)
        print(top_five[-5:])
        return top_five



def train(model, train_inputs, train_labels):
    average_loss = 0
    num_batches = len(train_inputs)//model.batch_size
    for i in range(num_batches):
        with tf.GradientTape() as tape:
            temp_inputs = train_inputs[i*model.batch_size:(i+1)*model.batch_size]
            temp_train_labels = train_labels[i*model.batch_size:(i+1)*model.batch_size]

            predictions = model.call(temp_inputs)
            loss = model.loss_function(predictions, temp_train_labels)
            average_loss += loss
            if i % 1000 == 0:
                print("---Batch", i, " Loss: ", loss)
        gradients = tape.gradient(loss, model.trainable_variables)
        model.optimizer.apply_gradients(zip(gradients, model.trainable_variables))
    print("****AVERAGE LOSS: ", average_loss / float(num_batches))

# Test the model by generating some samples.
def test(model, test_inputs, test_labels):
    # 4 batches with one image in each batch_inputs

    num_batches = len(test_inputs) // (model.batch_size)


    acc = 0
    for i in range(num_batches): # hardcode 15 because each i is an image
        # print("-------------batch", i, "-------------")
        batch_inputs = test_inputs[i * model.batch_size: (i+1) * model.batch_size]
        batch_labels = test_labels[i * model.batch_size: (i+1) * model.batch_size]

        batch_inputs = np.array(batch_inputs)
        batch_labels = np.array(batch_labels)

        print("batch labels shape:", batch_labels.shape)

        predictions = model.call(batch_inputs) # prediction for a single image

        batch_accuracy = model.total_accuracy(predictions, batch_labels)
        print("batch accuracy", batch_accuracy)
        acc += batch_accuracy

    average_accuracy = acc / float(num_batches)
    print("average accuracy:", average_accuracy)
    return average_accuracy

def test_single_img(model, image_path):
    # 4 batches with one image in each batch_inputs
    crops = []

    image = alter_image(image_path)
    image = resize_image(image, 96)
    cropped_images = generate_crop(image, 96, 10)

    for c in cropped_images:
        crops.append(c)

    predictions = model.call(crops) # prediction for a single image
    print(predictions.shape)
    top_5 = model.get_top_five(predictions)

    # print(top_5)


## --------------------------------------------------------------------------------------

def main():
    # Initialize generator and discriminator models
    model = DeepFont()
    model.load_weights('./weights_leaky_relu.h5', by_name=True)

    # For saving/loading models
    checkpoint_dir = './checkpoints_df_modified'
    checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt")
    checkpoint = tf.train.Checkpoint(model = model)
    manager = tf.train.CheckpointManager(checkpoint, checkpoint_dir, max_to_keep=3)
    # Ensure the output directory exists
    # if not os.path.exists(args.out_dir):
    #     os.makedirs(args.out_dir)

    if args.restore_checkpoint or args.mode == 'test' or args.mode == 'single_img':
        # restores the lates checkpoint using from the manager
        print("Running test mode...")
        checkpoint.restore(manager.latest_checkpoint)

    try:
        # Specify an invalid GPU device
        with tf.device('/device:' + args.device):
            if args.mode == 'train':
                train_inputs, train_labels = get_train()

                for epoch in range(0, args.num_epochs):
                    print('========================== EPOCH %d  ==========================' % epoch)
                    train(model, train_inputs, train_labels)
                    # Save at the end of the epoch, too
                    print("**** SAVING CHECKPOINT AT END OF EPOCH ****")
                    manager.save()
            if args.mode == 'test':
                test_inputs, test_labels = get_test()
                print("--test accuracy--", test(model, test_inputs, test_labels))
            if args.mode == "single_img":
                test_single_img(model, './BodoniStd93.png')
    except RuntimeError as e:
        print(e)

if __name__ == '__main__':
	main()
