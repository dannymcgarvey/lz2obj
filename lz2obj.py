import sys
import struct
import numpy as np

def angle(n):
    return (n / (2**16)) * 2 * np.pi

def T(x,y,z):
    return np.array([
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1]
    ])

def Rx(t):
    #=[1 0 0 0 ; 0 cos(t) -sin(t) 0;0 sin(t) cos(t) 0 ; 0 0 0 1];
    return np.array([
        [1, 0,          0,         0],
        [0, np.cos(t), -np.sin(t), 0],
        [0, np.sin(t),  np.cos(t), 0],
        [0, 0,          0,         1]
    ])

def Ry(t):
    #=[cos(t) 0 sin(t) 0;0 1 0 0;-sin(t) 0 cos(t) 0 ;0 0 0 1]
    return np.array([
        [ np.cos(t), 0, np.sin(t), 0],
        [ 0,         1, 0,         0],
        [-np.sin(t), 0, np.cos(t), 0],
        [ 0,         0, 0,         1]
    ])

def Rz(t):
    #[cos(t) -sin(t) 0 0;sin(t) cos(t) 0 0 ; 0 0 1 0; 0 0 0 1];
    return np.array([
        [np.cos(t), -np.sin(t), 0, 0],
        [np.sin(t),  np.cos(t), 0, 0],
        [0,          0,         1, 0],
        [0,          0,         0, 1]
    ])

fileContent = None
with open(sys.argv[1], mode="rb") as file: 
    fileContent = file.read()

if (len(sys.argv) == 3):
    output = open(sys.argv[2], "w")
elif (len(sys.argv) == 2):
    output = open("{}.obj".format(sys.argv[1]), "w")
else:
    print("usage: lz2obj.py <file.lz.raw> <output.obj>")
    print("message me on discord: glazier#8385")
    exit()

output.write("# OBJ file generated by lz2obj\n")
igCount, igOffset = struct.unpack(">II", fileContent[0x8:0x10])
triCount = 0
IG_LEN = 0x49C
for i in range(igCount):
    igHeader = fileContent[igOffset:igOffset+IG_LEN]
    igOffset += IG_LEN
    triangleOffset, tileOffset = struct.unpack(">II", igHeader[0x24:0x2C])
    tileCountX, tileCountY = struct.unpack(">II", igHeader[0x3C:0x44])
    tileCount = tileCountX * tileCountY
    modelCount, modelOffsetB = struct.unpack(">II", igHeader[0x94:0x9C])

    # get model names
    name = ""
    if modelCount == 0:
        name = "ItemGroup{}".format(i)
    else:
        fmtStr = ">" + "I" * modelCount
        modelBLen = modelCount * 4
        modelAList = list(struct.unpack(fmtStr, fileContent[modelOffsetB:modelOffsetB + modelBLen]))
        first = True
        for modelAOffset in modelAList:
            if not first:
                name += "+"
            (modelAPtr,) = struct.unpack(">I", fileContent[modelAOffset+8:modelAOffset+12])
            (nameOffset,) = struct.unpack(">I", fileContent[modelAPtr+4:modelAPtr+8])
            end = fileContent.index(b'\x00', nameOffset)
            name += str(fileContent[nameOffset:end], 'utf-8')
            first = False
        output.write("o {}\n".format(name))
        

    # get triangle list length
    maxInd = 0
    tileOffsets = struct.unpack(">" + tileCount * "I", fileContent[tileOffset:tileOffset + 4 * tileCount])
    for tile in tileOffsets:
        if tile == 0:
            continue
        end = tile - 1
        while (end - tile) % 2 != 0:
            end = fileContent.find(b'\xFF\xFF', end+1)
        inds = np.array(list(struct.unpack(">" + "H" * ((end-tile)//2),fileContent[tile:end])))
        best = np.max(inds)
        maxInd = max(maxInd, best)
    
    # extract collision triangles
    TRI_LEN = 0x40
    verts = list()
    normals = list()
    for j in range(maxInd + 1):
        triangle = fileContent[triangleOffset:triangleOffset+TRI_LEN]
        triangleOffset += TRI_LEN
        x1,y1,z1,xn,yn,zn,xr,yr,zr,flag,dx2,dy2,dx3,dy3=struct.unpack(">ffffffHHHHffff", triangle[0:0x30])
        P= np.array([
            [0, dx2, dx3],
            [0, dy2, dy3],
            [0, 0,   0  ],
            [1, 1,   1  ]
        ])
        xr, yr, zr = angle(xr), angle(yr), angle(zr)
        P = T(x1,y1,z1)  @ Ry(yr) @ Rx(xr) @ Rz(zr) @ P
        verts.append(P[0:3])
        normals.append((xn,yn,zn))
    # write vertices
    for j in range(len(verts)):
        for k in range(3):
            output.write("v {} {} {}\n".format(*(verts[j][:,k])))
    # write normals
    for j in range(len(normals)):
        output.write("vn {} {} {}\n".format(*normals[j]))
    # write faces
    for j in range(len(normals)):
        triCount += 1
        output.write("f {a1}//{c} {a2}//{c} {a3}//{c}\n".format(a1=3*triCount-2, a2=3*triCount-1, a3=3*triCount, c=triCount))


