import numpy as np
import skimage as ski

# def rigid_transform_3D(A, B):
#     assert A.shape == B.shape

#     num_rows, num_cols = A.shape
#     if num_rows != 3:
#         raise Exception(f"matrix A is not 3xN, it is {num_rows}x{num_cols}")

#     num_rows, num_cols = B.shape
#     if num_rows != 3:
#         raise Exception(f"matrix B is not 3xN, it is {num_rows}x{num_cols}")

#     # find mean column wise
#     centroid_A = np.mean(A, axis=1, dtype='float64',)
#     centroid_B = np.mean(B, axis=1, dtype='float64',)

#     # ensure centroids are 3x1
#     centroid_A = centroid_A.reshape(-1, 1)
#     centroid_B = centroid_B.reshape(-1, 1)

#     # subtract mean
#     Am = np.subtract(A, centroid_A, dtype='float64')
#     Bm = np.subtract(B, centroid_B, dtype='float64')

#     H = np.dot(Am, Bm.T).astype('float64')

#     # find rotation
#     U, _, Vt = np.linalg.svd(H)
#     R = np.dot(Vt.T, U.T)

#     # special reflection case
#     if np.linalg.det(R) < 0:
#         print('hello')
#         print("det(R) < R, reflection detected!, correcting for it ...")
#         Vt[2,:] *= -1
#         R = np.dot(Vt.T, U.T)

#     t = np.dot(-R, centroid_A) + centroid_B

#     return R, t

if __name__ == '__main__':
    x1 = 0
    y1 = 36
    
    x2 = 90
    y2 = 0

    x1_prime = 77
    y1_prime = -470.2
    
    x2_prime = 112
    y2_prime =-381
    

    # Define the source and destination coordinates
    src = np.array([[x1, y1], [x2, y2]])
    dest = np.array([[x1_prime, y1_prime], [x2_prime, y2_prime]])

    # Calculate the transformation matrix using the formula:
    # Destination = Source * TransformationMatrix
    #R,t = rigid_transform_3D(original, transformed)
    tform = ski.transform.EuclideanTransform()
    tform.estimate(src,dest)

    #vial_x = input("Enter x coordinate for vial: ")
    #vial_y = input("Enter y coordinate for vial: ")
    
    vial_coordinates = np.array([[0, 90], [36, 0], [1,1]])
    print(vial_coordinates)

    # Apply the affine transformation to the new point
    #new_point = ski.transform.warp(vial_coordinates, tform, output_shape=(2,2))
    new_point = np.dot(tform.params, vial_coordinates)
    print(new_point)